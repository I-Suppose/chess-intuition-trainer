import hashlib
import io
import shutil
import chess
import chess.engine
import chess.pgn
from sqlalchemy import delete, select
from app.core.config import settings
from app.database import SessionLocal
from app.models import ConnectedAccount, Game, GameAnalysis, GameStatus, Puzzle
from app.services.pgn_processor import opening_line as pgn_opening_line

PUZZLE_PRIORITY = {
    "Brilliant Move": 1,
    "Missed Brilliant Opportunity": 2,
    "Tactical Combination": 3,
    "Winning Move": 4,
    "Defensive Resource": 5,
    "Critical Decision": 6,
    "Great Move": 7,
    "Tactical Mistake": 8,
}
# Keep the library focused on the clearest decisions from each game. The full
# move-by-move analysis is still saved for the opening and progress views.
MAX_PUZZLES_PER_GAME = 3
PIECE_VALUE_CP = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900}


def _engine_path() -> str:
    candidates = [settings.stockfish_path, shutil.which("stockfish"), "/usr/games/stockfish", "/usr/bin/stockfish"]
    for candidate in candidates:
        if candidate and shutil.which(candidate):
            return candidate
    raise FileNotFoundError("Stockfish was not found. Install Stockfish or set STOCKFISH_PATH.")


def _score_data(score: chess.engine.PovScore, perspective: chess.Color = chess.WHITE) -> dict:
    value = score.pov(perspective)
    mate = value.mate()
    return {"type": "mate", "value": mate} if mate is not None else {"type": "cp", "value": value.score() or 0}


def _score_cp(score: chess.engine.PovScore, perspective: chess.Color) -> int:
    return score.pov(perspective).score(mate_score=100000) or 0


def _material(board: chess.Board, color: chess.Color) -> int:
    return sum(PIECE_VALUE_CP.get(piece.piece_type, 0) for piece in board.piece_map().values() if piece.color == color)


def _sacrifice(board: chess.Board, pv: list[chess.Move], color: chess.Color) -> bool:
    start = _material(board, color)
    lowest = start
    probe = board.copy()
    for move in pv[:8]:
        if move not in probe.legal_moves:
            break
        probe.push(move)
        lowest = min(lowest, _material(probe, color))
    return start - lowest >= 250


def _forcing(board: chess.Board, move: chess.Move) -> bool:
    return board.is_capture(move) or board.gives_check(move) or move.promotion is not None


def _classify(actual_best: bool, loss_cp: int, best_cp: int, second_gap: int, sacrifice: bool, forcing: bool):
    if actual_best and sacrifice and best_cp >= -100 and (second_gap >= 60 or forcing):
        return "BRILLIANT", "Brilliant Move", 0.94, "The played move is Stockfish's best choice and temporarily gives up material while preserving a sound position."
    if not actual_best and sacrifice and best_cp >= 0 and loss_cp >= 90:
        return "MISSED_OPPORTUNITY", "Missed Brilliant Opportunity", 0.9, "A sound material sacrifice was available, but the game continued with a substantially weaker move."
    if forcing and loss_cp >= 75:
        return ("BEST" if actual_best else "MISSED_OPPORTUNITY"), "Tactical Combination", 0.84, "The best continuation starts with a forcing check, capture, or promotion."
    if best_cp >= 300 and (forcing or second_gap >= 80) and (actual_best or loss_cp >= 75):
        return ("BEST" if actual_best else "MISSED_OPPORTUNITY"), "Winning Move", 0.8, "The engine's best continuation creates or preserves a decisive advantage."
    if best_cp <= 0 and second_gap >= 100 and not actual_best:
        return "MISSED_OPPORTUNITY", "Defensive Resource", 0.75, "One precise move is much stronger than the alternatives in a difficult position."
    if loss_cp >= 200:
        classification = "BLUNDER" if loss_cp >= 400 else "MISTAKE"
        return classification, "Tactical Mistake", 0.78, "The move gives up a large amount of evaluation compared with the engine's best move."
    if loss_cp >= 75:
        return "CRITICAL_POSITION", "Critical Decision", 0.7, "The move changes the evaluation enough to make this a meaningful decision point."
    if actual_best and second_gap >= 80 and best_cp >= -100:
        return "GREAT", "Great Move", 0.73, "The played move matches the engine's best choice in a position with a clear preference."
    return ("BEST" if actual_best else "GOOD"), None, 0.0, "No major turning point was detected at the configured analysis depth."


def _analyse_game(pgn: str, user_colour: str):
    parsed = chess.pgn.read_game(io.StringIO(pgn))
    if parsed is None or parsed.errors:
        raise ValueError("Cannot analyse an invalid PGN.")
    user_side = chess.WHITE if user_colour == "white" else chess.BLACK
    records = []
    with chess.engine.SimpleEngine.popen_uci(_engine_path()) as engine:
        engine.configure({"Threads": settings.stockfish_threads, "Hash": settings.stockfish_hash_mb})
        scan_limit = chess.engine.Limit(depth=min(settings.stockfish_depth, settings.stockfish_scan_depth), time=settings.stockfish_scan_time_limit)
        deep_limit = chess.engine.Limit(depth=settings.stockfish_depth, time=settings.stockfish_game_time_limit)
        board = parsed.board()
        for ply, actual_move in enumerate(parsed.mainline_moves(), start=1):
            if board.turn == user_side and not board.is_game_over():
                fen = board.fen()
                move_number = board.fullmove_number
                played_san = board.san(actual_move)
                infos = engine.analyse(board, scan_limit, multipv=min(2, settings.stockfish_multipv))
                if isinstance(infos, dict):
                    infos = [infos]
                infos = [info for info in infos if info.get("pv")]
                if not infos:
                    board.push(actual_move)
                    continue
                best = infos[0]
                best_move = best["pv"][0]
                best_score = best["score"]
                best_cp = _score_cp(best_score, user_side)
                best_pv = best["pv"]
                second_gap = 100000
                if len(infos) > 1:
                    second_gap = max(0, best_cp - _score_cp(infos[1]["score"], user_side))
                after_board = board.copy()
                after_board.push(actual_move)
                after_score = None
                if not after_board.is_game_over():
                    after_info = engine.analyse(after_board, scan_limit)
                    after_score = after_info["score"]
                    after_cp = _score_cp(after_score, user_side)
                else:
                    after_cp = best_cp
                scan_loss = max(0, best_cp - after_cp)
                scan_sacrifice = _sacrifice(board, best_pv, user_side)
                scan_forcing = _forcing(board, best_move)
                scan_actual_best = actual_move == best_move
                likely_turning_point = (scan_loss >= 75 or scan_sacrifice or
                                         (best_cp >= 280 and scan_forcing and scan_actual_best))
                if likely_turning_point:
                    infos = engine.analyse(board, deep_limit, multipv=settings.stockfish_multipv)
                    if isinstance(infos, dict):
                        infos = [infos]
                    infos = [info for info in infos if info.get("pv")]
                    if infos:
                        best = infos[0]
                        best_move = best["pv"][0]
                        best_score = best["score"]
                        best_cp = _score_cp(best_score, user_side)
                        best_pv = best["pv"]
                        second_gap = max(0, best_cp - _score_cp(infos[1]["score"], user_side)) if len(infos) > 1 else 100000
                        if not after_board.is_game_over():
                            after_info = engine.analyse(after_board, deep_limit)
                            after_score = after_info["score"]
                            after_cp = _score_cp(after_score, user_side)
                        else:
                            after_cp = best_cp
                loss_cp = max(0, best_cp - after_cp)
                sacrifice = _sacrifice(board, best_pv, user_side)
                forcing = _forcing(board, best_move)
                actual_best = actual_move == best_move
                classification, category, confidence, reason = _classify(actual_best, loss_cp, best_cp, second_gap, sacrifice, forcing)
                accepted = [info["pv"][0].uci() for info in infos if info.get("pv") and best_cp - _score_cp(info["score"], user_side) <= 25]
                variations = [{"move": info["pv"][0].uci(), "pv": [move.uci() for move in info["pv"]],
                               "score": _score_data(info["score"])} for info in infos if info.get("pv")]
                records.append({"ply": ply, "move_number": move_number, "fen": fen, "side_to_move": user_colour,
                                "played_move_uci": actual_move.uci(), "played_move_san": played_san, "best_move_uci": best_move.uci(),
                                "best_move_san": board.san(best_move), "alternative_moves": variations,
                                "evaluation_before": _score_data(best_score), "evaluation_after": _score_data(after_score) if after_score else None,
                                "principal_variation": [move.uci() for move in best_pv], "engine_depth": best.get("depth", 0),
                                "move_classification": classification, "classification_confidence": confidence,
                                "classification_reason": reason, "material_sacrifice": sacrifice, "category": category,
                                "priority": PUZZLE_PRIORITY.get(category, 99), "accepted_solutions": accepted or [best_move.uci()],
                                "loss_cp": loss_cp, "best_cp": best_cp, "before_cp": _score_cp(best_score, user_side),
                                "after_cp": after_cp, "best_gap_cp": second_gap, "forcing": forcing})
            board.push(actual_move)
    return records


def _fingerprint(fen: str) -> str:
    normalized = " ".join(fen.split()[:4])
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def analyse_position(fen: str) -> list[dict]:
    """Return full MultiPV continuations for an analysis-board position."""
    board = chess.Board(fen)
    with chess.engine.SimpleEngine.popen_uci(_engine_path()) as engine:
        engine.configure({"Threads": settings.stockfish_threads, "Hash": settings.stockfish_hash_mb})
        infos = engine.analyse(board,
                               chess.engine.Limit(depth=settings.stockfish_depth, time=settings.stockfish_time_limit),
                               multipv=max(3, settings.stockfish_multipv))
    if isinstance(infos, dict):
        infos = [infos]
    return [{"move": info["pv"][0].uci(), "pv": [move.uci() for move in info["pv"]],
             "score": _score_data(info["score"])} for info in infos if info.get("pv")]


def _explanation(record: dict, game: Game) -> str:
    opening = game.opening_name or "the opening was not named by the platform"
    line = game.opening_line or "the opening line is unavailable"
    text = f"From {opening} ({line}), Stockfish at depth {record['engine_depth']} selected {record['best_move_san']} as the strongest move. {record['classification_reason']}"
    if record["played_move_uci"] != record["best_move_uci"]:
        text += f" The game continued with {record['played_move_san']}; the best move was about {record['loss_cp']} centipawns better for your side in this analysis."
    return text


def analyse_game(game_id: str):
    import uuid
    game_uuid = uuid.UUID(game_id)
    db = SessionLocal()
    try:
        game = db.get(Game, game_uuid)
        if not game:
            return
        game.analysis_status = GameStatus.analysing
        db.commit()
        game_data = {"id": game.id, "pgn": game.pgn, "user_colour": game.user_colour, "opening_name": game.opening_name,
                     "opening_line": pgn_opening_line(game.pgn), "account_id": game.account_id}
        game_id_value = game.id
        account_id = game.account_id
        db.close()

        records = _analyse_game(game_data["pgn"], game_data["user_colour"] or "white")
        candidates = [record for record in records if record["category"]]
        candidates.sort(key=lambda record: (
            record["loss_cp"],
            record["best_gap_cp"],
            record["priority"] * -1,
        ), reverse=True)
        selected_puzzles = {record["ply"] for record in candidates[:MAX_PUZZLES_PER_GAME]}
        db = SessionLocal()
        game = db.get(Game, game_id_value)
        account = db.get(ConnectedAccount, account_id)
        if not game or not account:
            return
        game.opening_line = game_data["opening_line"]
        db.execute(delete(GameAnalysis).where(GameAnalysis.game_id == game.id))
        seen_fingerprints = set()
        for record in records:
            analysis = GameAnalysis(game_id=game.id, move_number=record["move_number"], ply=record["ply"], fen=record["fen"],
                                    side_to_move=record["side_to_move"], played_move_uci=record["played_move_uci"], best_move_uci=record["best_move_uci"],
                                    alternative_moves=record["alternative_moves"], evaluation_before=record["evaluation_before"],
                                    evaluation_after=record["evaluation_after"], principal_variation=record["principal_variation"],
                                    engine_depth=record["engine_depth"], move_classification=record["move_classification"],
                                    classification_confidence=record["classification_confidence"], classification_reason=record["classification_reason"],
                                    material_sacrifice=record["material_sacrifice"])
            db.add(analysis)
            db.flush()
            if record["category"] and record["ply"] in selected_puzzles:
                fingerprint = _fingerprint(record["fen"])
                duplicate = fingerprint in seen_fingerprints or db.scalar(select(Puzzle.id).where(Puzzle.user_id == account.user_id, Puzzle.position_fingerprint == fingerprint))
                seen_fingerprints.add(fingerprint)
                if not duplicate:
                    db.add(Puzzle(user_id=account.user_id, game_id=game.id, analysis_id=analysis.id,
                                  position_fingerprint=fingerprint, fen=record["fen"], side_to_move=record["side_to_move"],
                                  puzzle_category=record["category"], priority=record["priority"], solution_uci=record["best_move_uci"],
                                  accepted_solutions=record["accepted_solutions"], principal_variation=record["principal_variation"],
                                  explanation=_explanation(record, game), game_move_number=record["move_number"]))
                    db.flush()
        game.analysis_status = GameStatus.analysed
        db.commit()
    except Exception:
        db.rollback()
        failed_game = db.get(Game, game_uuid)
        if failed_game:
            failed_game.analysis_status = GameStatus.failed
            db.commit()
        raise
    finally:
        db.close()
