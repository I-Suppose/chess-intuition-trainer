import uuid
import logging
from sqlalchemy import select, text, update
from app.database import SessionLocal, engine
from app.models import ConnectedAccount, Game, GameStatus
from app.services.stockfish_analyzer import analyse_game
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, autoretry_for=(OSError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 2})
def analyze_pending_games(self, account_id: str):
    account_uuid = uuid.UUID(account_id)
    lock_connection = engine.connect()
    try:
        acquired = lock_connection.scalar(text("SELECT pg_try_advisory_lock(hashtext(:key))"), {"key": account_id})
        if not acquired:
            return {"status": "already_running"}
        db = SessionLocal()
        try:
            account = db.get(ConnectedAccount, account_uuid)
            if not account:
                return {"status": "account_missing"}
            db.execute(update(Game).where(Game.account_id == account_uuid, Game.analysis_status == GameStatus.analysing)
                       .values(analysis_status=GameStatus.pending))
            db.commit()
            game_ids = db.scalars(select(Game.id).where(Game.account_id == account_uuid,
                                                        Game.import_status == GameStatus.imported,
                                                        Game.analysis_status == GameStatus.pending)
                                 .order_by(Game.played_at.desc().nullslast(), Game.id)).all()
        finally:
            db.close()
        completed = 0
        failed = 0
        for game_id in game_ids:
            try:
                analyse_game(str(game_id))
                completed += 1
            except Exception:
                logger.exception("Game analysis failed for game %s", game_id)
                failed += 1
        return {"analysed": completed, "failed": failed}
    finally:
        try:
            lock_connection.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": account_id})
        finally:
            lock_connection.close()
