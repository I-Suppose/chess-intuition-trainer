import uuid
import httpx
import chess
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.auth import current_user
from app.database import get_db
from app.models import ConnectedAccount, Game, GameAnalysis, GameStatus, Platform, Puzzle, PuzzleAttempt, SyncStatus, User
from app.schemas import AccountConnect, AccountOut, GameOut, PuzzleAttemptIn, PuzzleAttemptOut, PuzzleSolutionOut
from app.workers.import_tasks import import_account_games
from app.integrations import chesscom
from app.services.pgn_processor import opening_line as pgn_opening_line

router = APIRouter(prefix="/api/v1")


def owned_account(db: Session, account_id: uuid.UUID, user: User):
    account = db.scalar(select(ConnectedAccount).where(ConnectedAccount.id == account_id, ConnectedAccount.user_id == user.id))
    if not account:
        raise HTTPException(404, "Connected account not found.")
    return account


def queue_import(account_id: uuid.UUID, older: bool = False):
    try:
        return import_account_games.delay(str(account_id), older=older)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="The game import queue is unavailable. Your account is saved; please retry shortly.") from exc


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
        existing.sync_status = SyncStatus.pending
        db.commit()
        queue_import(existing.id)
        account = existing
    else:
        account = ConnectedAccount(user_id=user.id, platform=payload.platform, username=username)
        db.add(account)
        db.commit()
        db.refresh(account)
        queue_import(account.id)
    game_count = db.scalar(select(func.count(Game.id)).where(Game.account_id == account.id)) or 0
    return AccountOut(id=account.id, platform=account.platform, username=account.username, last_synced_at=account.last_synced_at, sync_status=account.sync_status, game_count=game_count)


@router.post("/accounts/{account_id}/sync", status_code=202)
def sync(account_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    account = owned_account(db, account_id, user)
    queue_import(account.id)
    return {"status": "queued"}


@router.post("/games/import-older", status_code=202)
def import_older(account_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    account = owned_account(db, account_id, user)
    queue_import(account.id, older=True)
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


def _opening_profile(db: Session, user: User):
    rows = db.execute(select(Game, ConnectedAccount.platform).join(ConnectedAccount).where(ConnectedAccount.user_id == user.id,
                                                                                      Game.import_status == GameStatus.imported)).all()
    grouped = {}
    for game, platform in rows:
        name = game.opening_name or "Opening not classified"
        line = game.opening_line or pgn_opening_line(game.pgn) or "Line unavailable"
        item = grouped.setdefault(name, {"name": name, "games": 0, "wins": 0, "draws": 0, "losses": 0, "lines": {}})
        item["games"] += 1
        if game.result == "win":
            item["wins"] += 1
        elif game.result == "draw":
            item["draws"] += 1
        elif game.result == "loss":
            item["losses"] += 1
        line_key = f"{game.user_colour or 'unknown'}|{line}"
        line_item = item["lines"].setdefault(line_key, {"line": line, "user_colour": game.user_colour, "games": 0, "wins": 0, "draws": 0, "losses": 0})
        line_item["games"] += 1
        if game.result in ("win", "draw", "loss"):
            result_key = {"win": "wins", "draw": "draws", "loss": "losses"}[game.result]
            line_item[result_key] += 1
    result = []
    for item in grouped.values():
        games_count = item["games"]
        item["score_rate"] = round((item["wins"] + item["draws"] * 0.5) / games_count * 100, 1) if games_count else 0
        item["lines"] = sorted(item["lines"].values(), key=lambda line: (-line["games"], line["line"]))
        result.append(item)
    return sorted(result, key=lambda item: (-item["games"], item["name"]))


@router.get("/openings")
def openings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = _opening_profile(db, user)
    return {"openings": items, "total_games": sum(item["games"] for item in items)}


@router.get("/games/{game_id}/analysis")
def game_analysis(game_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned = db.scalar(select(Game.id).join(ConnectedAccount).where(Game.id == game_id, ConnectedAccount.user_id == user.id))
    if not owned:
        raise HTTPException(404, "Game not found.")
    rows = db.scalars(select(GameAnalysis).where(GameAnalysis.game_id == game_id).order_by(GameAnalysis.ply)).all()
    return [{"move_number": row.move_number, "ply": row.ply, "fen": row.fen, "side_to_move": row.side_to_move,
             "played_move_uci": row.played_move_uci, "best_move_uci": row.best_move_uci,
             "alternative_moves": row.alternative_moves, "evaluation_before": row.evaluation_before,
             "evaluation_after": row.evaluation_after, "principal_variation": row.principal_variation,
             "engine_depth": row.engine_depth, "move_classification": row.move_classification,
             "classification_confidence": row.classification_confidence, "classification_reason": row.classification_reason,
             "material_sacrifice": row.material_sacrifice} for row in rows]


@router.post("/games/{game_id}/analysis/retry", status_code=202)
def retry_game_analysis(game_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.scalar(select(Game).join(ConnectedAccount).where(Game.id == game_id, ConnectedAccount.user_id == user.id))
    if not row:
        raise HTTPException(404, "Game not found.")
    if row.import_status != GameStatus.imported:
        raise HTTPException(409, "This game was not imported with a valid PGN.")
    if row.analysis_status == GameStatus.analysing:
        raise HTTPException(409, "This game is already being analysed.")
    row.analysis_status = GameStatus.pending
    db.commit()
    from app.workers.analysis_tasks import analyze_pending_games
    try:
        analyze_pending_games.delay(str(row.account_id))
    except Exception as exc:
        raise HTTPException(503, "Analysis queue is unavailable. Retry in a moment.") from exc
    return {"status": "queued"}


@router.get("/puzzles")
def puzzles(category: str | None = None, completed: bool | None = None, platform: Platform | None = None,
            opening: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=100),
            db: Session = Depends(get_db), user: User = Depends(current_user)):
    solved_ids = select(PuzzleAttempt.puzzle_id).where(PuzzleAttempt.user_id == user.id, PuzzleAttempt.is_correct.is_(True)).distinct()
    query = select(Puzzle, Game, ConnectedAccount).join(Game, Puzzle.game_id == Game.id).join(ConnectedAccount, Game.account_id == ConnectedAccount.id).where(Puzzle.user_id == user.id)
    if category:
        query = query.where(Puzzle.puzzle_category == category)
    if platform:
        query = query.where(ConnectedAccount.platform == platform)
    if opening:
        query = query.where(Game.opening_name == opening)
    if completed is True:
        query = query.where(Puzzle.id.in_(solved_ids))
    elif completed is False:
        query = query.where(~Puzzle.id.in_(solved_ids))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(Puzzle.priority, Game.played_at.desc().nullslast(), Puzzle.game_move_number, Puzzle.created_at)
                      .offset((page - 1) * page_size).limit(page_size)).all()
    solved_set = set(db.scalars(solved_ids).all())
    items = []
    for puzzle, game, account in rows:
        items.append({"id": puzzle.id, "category": puzzle.puzzle_category, "priority": puzzle.priority, "fen": puzzle.fen,
                      "side_to_move": puzzle.side_to_move, "game_move_number": puzzle.game_move_number,
                      "opening_name": game.opening_name, "opening_line": game.opening_line,
                      "opponent_username": game.opponent_username, "played_at": game.played_at,
                      "platform": account.platform, "game_url": game.game_url,
                      "completed": puzzle.id in solved_set, "explanation": puzzle.explanation if puzzle.id in solved_set else None})
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _owned_puzzle(db: Session, puzzle_id: uuid.UUID, user: User):
    row = db.execute(select(Puzzle, Game, ConnectedAccount).join(Game, Puzzle.game_id == Game.id)
                     .join(ConnectedAccount, Game.account_id == ConnectedAccount.id)
                     .where(Puzzle.id == puzzle_id, Puzzle.user_id == user.id, ConnectedAccount.user_id == user.id)).first()
    if not row:
        raise HTTPException(404, "Puzzle not found.")
    return row


@router.get("/puzzles/{puzzle_id}")
def puzzle(puzzle_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item, game, account = _owned_puzzle(db, puzzle_id, user)
    solved = db.scalar(select(PuzzleAttempt.id).where(PuzzleAttempt.user_id == user.id, PuzzleAttempt.puzzle_id == item.id,
                                                      PuzzleAttempt.is_correct.is_(True)).limit(1)) is not None
    attempts = db.scalar(select(func.count(PuzzleAttempt.id)).where(PuzzleAttempt.user_id == user.id, PuzzleAttempt.puzzle_id == item.id)) or 0
    return {"id": item.id, "category": item.puzzle_category, "priority": item.priority, "fen": item.fen,
            "side_to_move": item.side_to_move, "game_move_number": item.game_move_number,
            "opening_name": game.opening_name, "opening_line": game.opening_line,
            "opponent_username": game.opponent_username, "played_at": game.played_at,
            "platform": account.platform, "game_url": game.game_url, "completed": solved,
            "attempt_count": attempts, "explanation": item.explanation if solved else None}


@router.post("/puzzles/{puzzle_id}/attempt", response_model=PuzzleAttemptOut)
def submit_puzzle_attempt(puzzle_id: uuid.UUID, payload: PuzzleAttemptIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item, _, _ = _owned_puzzle(db, puzzle_id, user)
    try:
        move = chess.Move.from_uci(payload.move_uci)
        board = chess.Board(item.fen)
    except ValueError as exc:
        raise HTTPException(422, "Move or puzzle position is invalid.") from exc
    if move not in board.legal_moves:
        raise HTTPException(422, "That move is not legal in this position.")
    accepted = item.accepted_solutions or [item.solution_uci]
    correct = move.uci() in accepted
    attempt = PuzzleAttempt(user_id=user.id, puzzle_id=item.id, submitted_move=move.uci(), is_correct=correct, time_taken=payload.time_taken)
    db.add(attempt)
    db.commit()
    return PuzzleAttemptOut(attempt_id=attempt.id, is_correct=correct,
                            message="Correct. Review the continuation and opening context." if correct else "Not the engine's best move. Try again or reveal the line after another attempt.")


@router.get("/puzzles/{puzzle_id}/solution", response_model=PuzzleSolutionOut)
def puzzle_solution(puzzle_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item, game, _ = _owned_puzzle(db, puzzle_id, user)
    attempted = db.scalar(select(PuzzleAttempt.id).where(PuzzleAttempt.user_id == user.id, PuzzleAttempt.puzzle_id == item.id).limit(1))
    if not attempted:
        raise HTTPException(403, "Submit a move before viewing the solution.")
    board = chess.Board(item.fen)
    solution = chess.Move.from_uci(item.solution_uci)
    solution_san = board.san(solution)
    analysis = db.get(GameAnalysis, item.analysis_id)
    played_san = None
    if analysis:
        try:
            played_san = board.san(chess.Move.from_uci(analysis.played_move_uci))
        except ValueError:
            pass
    pv_san = []
    for move_uci in (item.principal_variation or []):
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            break
        pv_san.append(board.san(move))
        board.push(move)
    return PuzzleSolutionOut(solution_move_uci=item.solution_uci, solution_move_san=solution_san,
                             principal_variation_uci=item.principal_variation or [], principal_variation_san=pv_san,
                             explanation=item.explanation, played_move_san=played_san)


@router.get("/progress")
def progress(db: Session = Depends(get_db), user: User = Depends(current_user)):
    account_ids = select(ConnectedAccount.id).where(ConnectedAccount.user_id == user.id)
    total_games = db.scalar(select(func.count(Game.id)).where(Game.account_id.in_(account_ids), Game.import_status == GameStatus.imported)) or 0
    pending = db.scalar(select(func.count(Game.id)).where(Game.account_id.in_(account_ids), Game.analysis_status.in_([GameStatus.pending, GameStatus.analysing]))) or 0
    failed = db.scalar(select(func.count(Game.id)).where(Game.account_id.in_(account_ids), Game.analysis_status == GameStatus.failed)) or 0
    analysed = db.scalar(select(func.count(Game.id)).where(Game.account_id.in_(account_ids), Game.analysis_status == GameStatus.analysed)) or 0
    total_puzzles = db.scalar(select(func.count(Puzzle.id)).where(Puzzle.user_id == user.id)) or 0
    brilliant = db.scalar(select(func.count(Puzzle.id)).where(Puzzle.user_id == user.id, Puzzle.puzzle_category == "Brilliant Move")) or 0
    completed = db.scalar(select(func.count(func.distinct(PuzzleAttempt.puzzle_id))).where(PuzzleAttempt.user_id == user.id, PuzzleAttempt.is_correct.is_(True))) or 0
    return {"games_imported": total_games, "puzzles_generated": total_puzzles, "brilliant_puzzles": brilliant,
            "completed_puzzles": completed, "analysis_pending": pending, "analysis_failed": failed, "analysis_complete": analysed,
            "top_openings": _opening_profile(db, user)[:5]}


@router.get("/progress/history")
def progress_history(page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100),
                     db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = select(PuzzleAttempt, Puzzle, Game).join(Puzzle, PuzzleAttempt.puzzle_id == Puzzle.id).join(Game, Puzzle.game_id == Game.id).where(PuzzleAttempt.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(PuzzleAttempt.attempted_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [{"attempted_at": attempt.attempted_at, "is_correct": attempt.is_correct,
                       "submitted_move": attempt.submitted_move, "category": item.puzzle_category,
                       "opening_name": game.opening_name, "game_move_number": item.game_move_number,
                       "puzzle_id": item.id} for attempt, item, game in rows], "total": total, "page": page, "page_size": page_size}
