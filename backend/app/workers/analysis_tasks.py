from __future__ import annotations
import logging
import uuid
from celery import group
from sqlalchemy import select, update
from app.database import SessionLocal
from app.models import ConnectedAccount, Game, GameStatus
from app.services.stockfish_analyzer import analyse_game
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def analyze_pending_games(self, account_id: str):
    """Claim pending games quickly and let Celery analyze them in parallel."""
    account_uuid = uuid.UUID(account_id)
    db = SessionLocal()
    try:
        account = db.get(ConnectedAccount, account_uuid)
        if not account or not account.is_connected:
            return {"status": "account_missing_or_disconnected", "queued": 0}
        games = db.scalars(
            select(Game)
            .where(Game.account_id == account_uuid,
                   Game.import_status == GameStatus.imported,
                   Game.analysis_status == GameStatus.pending)
            .order_by(Game.played_at.desc().nullslast(), Game.id)
            .with_for_update(skip_locked=True)
        ).all()
        game_ids = [game.id for game in games]
        for game in games:
            game.analysis_status = GameStatus.analysing
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if not game_ids:
        return {"status": "nothing_to_queue", "queued": 0}
    try:
        group(analyze_one_game.s(str(game_id)) for game_id in game_ids).apply_async()
    except Exception:
        recovery = SessionLocal()
        try:
            recovery.execute(update(Game).where(Game.id.in_(game_ids),
                                                Game.analysis_status == GameStatus.analysing)
                             .values(analysis_status=GameStatus.pending))
            recovery.commit()
        finally:
            recovery.close()
        raise
    return {"status": "queued", "queued": len(game_ids)}


@celery_app.task(bind=True, autoretry_for=(OSError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 2})
def analyze_one_game(self, game_id: str):
    try:
        analyse_game(game_id)
        return {"status": "analysed", "game_id": game_id}
    except Exception:
        logger.exception("Game analysis failed for game %s", game_id)
        raise
