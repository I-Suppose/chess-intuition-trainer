import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from redis import Redis
from app.database import SessionLocal
from app.models import ConnectedAccount, Game, GameStatus, Platform, SyncStatus
from app.core.config import settings
from app.workers.celery_app import celery_app
from app.integrations import chesscom, lichess
from app.integrations.errors import RateLimitError
from app.services.pgn_processor import normalize_pgn, opening_line, opening_name


def _save(account_id: str, older: bool = False):
    db = SessionLocal()
    account = None
    try:
        account = db.get(ConnectedAccount, uuid.UUID(account_id))
        if not account:
            return
        account.sync_status = SyncStatus.importing
        db.commit()
        oldest = db.scalar(select(Game.played_at).where(Game.account_id == account.id, Game.played_at.is_not(None)).order_by(Game.played_at.asc()).limit(1))
        if account.platform == Platform.chesscom:
            data = asyncio.run(chesscom.fetch_games(account.username, settings.initial_game_import_limit, oldest if older else None))
        else:
            before_ms = int(oldest.timestamp() * 1000) if older and oldest else None
            data = asyncio.run(lichess.fetch_games(account.username, settings.initial_game_import_limit, before_ms))
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
        account.last_synced_at = datetime.now(timezone.utc)
        account.sync_status = SyncStatus.imported
        db.commit()
        from app.workers.analysis_tasks import analyze_pending_games
        analyze_pending_games.delay(str(account.id))
    except Exception:
        db.rollback()
        if account:
            account.sync_status = SyncStatus.failed
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, autoretry_for=(OSError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 3})
def import_account_games(self, account_id: str, older: bool = False):
    lock_client = Redis.from_url(settings.redis_url)
    lock = lock_client.lock(f"account-import:{account_id}", timeout=1200, blocking_timeout=0)
    try:
        if not lock.acquire():
            return {"status": "already_running"}
        _save(account_id, older)
    except RateLimitError as exc:
        raise self.retry(exc=exc, countdown=min(exc.retry_after, 900), max_retries=3)
    finally:
        if lock.owned():
            lock.release()
        lock_client.close()
