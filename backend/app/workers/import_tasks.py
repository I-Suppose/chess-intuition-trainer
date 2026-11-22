import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, text
from app.database import SessionLocal, engine
from app.models import ConnectedAccount, Game, GameStatus, Platform, SyncStatus
from app.core.config import settings
from app.workers.celery_app import celery_app
from app.integrations import chesscom, lichess
from app.integrations.errors import RateLimitError
from app.services.pgn_processor import normalize_pgn, opening_line, opening_name

logger = logging.getLogger(__name__)


def _save(account_id: str, older: bool = False, limit: int | None = None):
    db = SessionLocal()
    account = None
    try:
        account = db.get(ConnectedAccount, uuid.UUID(account_id))
        if not account:
            return
        account.sync_status = SyncStatus.importing
        db.commit()
        batch_limit = max(1, min(limit or settings.initial_game_import_limit, 1000))
        oldest = db.scalar(select(Game.played_at).where(Game.account_id == account.id, Game.played_at.is_not(None)).order_by(Game.played_at.asc()).limit(1))
        if account.platform == Platform.chesscom:
            data = asyncio.run(chesscom.fetch_games(account.username, batch_limit, oldest if older else None))
        else:
            before_ms = int(oldest.timestamp() * 1000) if older and oldest else None
            data = asyncio.run(lichess.fetch_games(account.username, batch_limit, before_ms))
        imported_count = 0
        for game in data:
            if not game["id"] or not game["pgn"]:
                continue
            exists = db.scalar(select(Game.id).where(Game.account_id == account.id, Game.platform_game_id == str(game["id"])))
            if exists:
                continue
            try:
                pgn = normalize_pgn(game["pgn"])
                import_status = GameStatus.imported
                line = opening_line(pgn)
                name = game["opening"] or opening_name(pgn)
            except ValueError:
                pgn = game["pgn"]
                import_status = GameStatus.failed
                line = None
                name = game["opening"]
            db.add(Game(account_id=account.id, platform_game_id=str(game["id"]), game_url=game["url"], white_player=game["white"],
                        black_player=game["black"], user_colour=game["user_colour"], opponent_username=game["opponent"], result=game["result"],
                        played_at=game["played_at"], time_control=game["time_control"], opening_name=name, opening_line=line, pgn=pgn,
                        import_status=import_status, analysis_status=GameStatus.pending))
            imported_count += import_status == GameStatus.imported
        account.last_synced_at = datetime.now(timezone.utc)
        account.sync_status = SyncStatus.imported
        db.commit()
        logger.info(
            "Imported %s new games for account %s (%s); fetched %s game records",
            imported_count,
            account.id,
            account.platform.value,
            len(data),
        )
        from app.workers.analysis_tasks import analyze_pending_games
        analyze_pending_games.delay(str(account.id))
    except Exception:
        db.rollback()
        if account:
            account.sync_status = SyncStatus.failed
            db.commit()
            logger.exception("Game import failed for account %s (%s)", account.id, account.platform.value)
        raise
    finally:
        db.close()


@celery_app.task(bind=True, autoretry_for=(OSError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 3})
def import_account_games(self, account_id: str, older: bool = False, limit: int | None = None):
    on_vercel = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))
    logger.info("Starting game import for account %s (older=%s, limit=%s)", account_id, older, limit)
    lock_client = None
    lock = None
    lock_connection = None
    if on_vercel:
        # Session advisory locks work across Vercel function instances without
        # a separate, always-on Redis service.
        key = int.from_bytes(hashlib.sha256(account_id.encode("utf-8")).digest()[:8], "big", signed=True)
        lock_connection = engine.connect()
        try:
            acquired = lock_connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar()
        except Exception:
            lock_connection.invalidate()
            lock_connection.close()
            raise
        if not acquired:
            lock_connection.close()
            return {"status": "already_running"}
    else:
        from redis import Redis
        lock_client = Redis.from_url(settings.redis_url)
        lock = lock_client.lock(f"account-import:{account_id}", timeout=1200, blocking_timeout=0)
    try:
        if lock is not None and not lock.acquire():
            return {"status": "already_running"}
        _save(account_id, older, limit)
    except RateLimitError as exc:
        raise self.retry(exc=exc, countdown=min(exc.retry_after, 900), max_retries=3)
    finally:
        if lock is not None and lock.owned():
            lock.release()
        if lock_client is not None:
            lock_client.close()
        if lock_connection is not None:
            try:
                lock_connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
            except Exception:
                # Closing a pooled connection alone would not clear a
                # session-level advisory lock if the unlock query failed.
                lock_connection.invalidate()
            finally:
                lock_connection.close()
