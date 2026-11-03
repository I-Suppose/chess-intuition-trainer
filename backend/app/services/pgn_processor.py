import io
import chess.pgn


def normalize_pgn(raw: str) -> str:
    """Parse and safely re-export one game without comments or side variations."""
    game = chess.pgn.read_game(io.StringIO(raw))
    if game is None or game.errors:
        raise ValueError("The game PGN is invalid or incomplete.")
    return game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False))
