import io
import chess.pgn


def normalize_pgn(raw: str) -> str:
    """Parse and safely re-export one game without comments or side variations."""
    game = chess.pgn.read_game(io.StringIO(raw))
    if game is None or game.errors:
        raise ValueError("The game PGN is invalid or incomplete.")
    return game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False))


def opening_line(raw: str, plies: int = 12) -> str | None:
    game = chess.pgn.read_game(io.StringIO(raw))
    if game is None:
        return None
    board = game.board()
    moves = []
    for move in game.mainline_moves():
        if len(moves) >= plies:
            break
        number = board.fullmove_number
        san = board.san(move)
        if board.turn == chess.WHITE:
            moves.append(f"{number}. {san}")
        else:
            if moves:
                moves[-1] += f" {san}"
            else:
                moves.append(f"{number}... {san}")
        board.push(move)
    return " ".join(moves) or None


def opening_name(raw: str) -> str | None:
    game = chess.pgn.read_game(io.StringIO(raw))
    if game is None:
        return None
    return game.headers.get("Opening") or game.headers.get("ECOUrl") or game.headers.get("ECO")
