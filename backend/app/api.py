import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.auth import current_user
from app.database import get_db
from app.models import ConnectedAccount, Game, Platform, User
from app.schemas import AccountConnect, AccountOut, GameOut
from app.workers.import_tasks import import_account_games
from app.integrations import chesscom

router = APIRouter(prefix="/api/v1")


def owned_account(db: Session, account_id: uuid.UUID, user: User):
    account = db.scalar(select(ConnectedAccount).where(ConnectedAccount.id == account_id, ConnectedAccount.user_id == user.id))
    if not account:
        raise HTTPException(404, "Connected account not found.")
    return account


@router.get("/accounts", response_model=list[AccountOut])
def accounts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.execute(select(ConnectedAccount, func.count(Game.id)).outerjoin(Game).where(ConnectedAccount.user_id == user.id, ConnectedAccount.is_connected.is_(True)).group_by(ConnectedAccount.id).order_by(ConnectedAccount.connected_at.desc())).all()
    return [AccountOut(id=a.id, platform=a.platform, username=a.username, last_synced_at=a.last_synced_at, sync_status=a.sync_status, game_count=count) for a, count in rows]


@router.post("/accounts/connect", response_model=AccountOut, status_code=202)
async def connect(payload: AccountConnect, db: Session = Depends(get_db), user: User = Depends(current_user)):
    username = payload.username.strip()
    try:
        async with httpx.AsyncClient(timeout=15, headers=chesscom.HEADERS if payload.platform == Platform.chesscom else {"User-Agent": "ChessIntuitionTrainer/0.1"}) as client:
            url = f"{chesscom.BASE}/player/{username}" if payload.platform == Platform.chesscom else f"https://lichess.org/api/user/{username}"
            response = await client.get(url)
            if response.status_code == 404:
                raise HTTPException(404, f"{payload.platform.value} username was not found.")
            response.raise_for_status()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Could not validate that account right now. Please try again.") from exc
    existing = db.scalar(select(ConnectedAccount).where(ConnectedAccount.user_id == user.id, ConnectedAccount.platform == payload.platform, func.lower(ConnectedAccount.username) == username.lower()))
    if existing:
        existing.is_connected = True
        import_account_games.delay(str(existing.id))
        account = existing
    else:
        account = ConnectedAccount(user_id=user.id, platform=payload.platform, username=username)
        db.add(account)
        db.commit()
        db.refresh(account)
        import_account_games.delay(str(account.id))
    game_count = db.scalar(select(func.count(Game.id)).where(Game.account_id == account.id)) or 0
    return AccountOut(id=account.id, platform=account.platform, username=account.username, last_synced_at=account.last_synced_at, sync_status=account.sync_status, game_count=game_count)


@router.post("/accounts/{account_id}/sync", status_code=202)
def sync(account_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    account = owned_account(db, account_id, user)
    import_account_games.delay(str(account.id))
    return {"status": "queued"}


@router.post("/games/import-older", status_code=202)
def import_older(account_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    account = owned_account(db, account_id, user)
    import_account_games.delay(str(account.id), older=True)
    return {"status": "queued"}


@router.delete("/accounts/{account_id}", status_code=204)
def disconnect(account_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    account = owned_account(db, account_id, user)
    account.is_connected = False
    db.commit()


@router.get("/games", response_model=list[GameOut])
def games(page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100), platform: Platform | None = None,
          db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = select(Game).join(ConnectedAccount).where(ConnectedAccount.user_id == user.id)
    if platform:
        query = query.where(ConnectedAccount.platform == platform)
    return db.scalars(query.order_by(Game.played_at.desc().nullslast(), Game.id).offset((page - 1) * page_size).limit(page_size)).all()


@router.get("/games/{game_id}", response_model=GameOut)
def game(game_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.scalar(select(Game).join(ConnectedAccount).where(Game.id == game_id, ConnectedAccount.user_id == user.id))
    if not row:
        raise HTTPException(404, "Game not found.")
    return row


@router.get("/progress")
def progress(db: Session = Depends(get_db), user: User = Depends(current_user)):
    account_ids = select(ConnectedAccount.id).where(ConnectedAccount.user_id == user.id)
    total = db.scalar(select(func.count(Game.id)).where(Game.account_id.in_(account_ids))) or 0
    return {"games_imported": total, "puzzles_generated": 0, "brilliant_puzzles": 0, "completed_puzzles": 0, "analysis_pending": total}


@router.get("/puzzles")
def puzzles(user: User = Depends(current_user)):
    return {"items": [], "total": 0, "message": "Puzzle generation and Stockfish analysis are not implemented in this version."}
