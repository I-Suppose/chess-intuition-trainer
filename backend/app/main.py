import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import router
from app.database import SessionLocal
from app.models import ConnectedAccount, Game, GameStatus
from sqlalchemy import select

app = FastAPI(title="Chess Intuition Trainer API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[item.strip() for item in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

logger = logging.getLogger(__name__)


@app.on_event("startup")
def queue_existing_games_for_analysis():
    from app.workers.analysis_tasks import analyze_pending_games
    db = SessionLocal()
    try:
        account_ids = db.scalars(select(ConnectedAccount.id).join(Game).where(
            ConnectedAccount.is_connected.is_(True), Game.import_status == GameStatus.imported,
            Game.analysis_status.in_([GameStatus.pending, GameStatus.analysing])).distinct()).all()
    finally:
        db.close()
    for account_id in account_ids:
        try:
            analyze_pending_games.delay(str(account_id))
        except Exception:
            logger.exception("Could not queue pending analysis for account %s", account_id)


@app.get("/health")
def health():
    return {"status": "ok"}
