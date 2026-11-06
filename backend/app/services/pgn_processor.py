import io
import re
import chess.pgn


def opening_family(name: str | None) -> str:
    """Collapse named opening variations to a player-friendly family label."""
    value = re.sub(r"\s+", " ", (name or "").replace("’", "'").strip())
    if not value:
        return "Opening not classified"
    families = [
        (r"queen'?s gambit", "Queen's Gambit"), (r"queen'?s pawn", "Queen's Pawn Openings"),
        (r"king'?s indian", "King's Indian Defense"), (r"king'?s gambit", "King's Gambit"),
        (r"queen'?s indian", "Queen's Indian Defense"), (r"nimzo[- ]indian", "Nimzo-Indian Defense"),
        (r"caro[- ]?kann", "Caro-Kann Defense"), (r"sicilian", "Sicilian Defense"),
        (r"french", "French Defense"), (r"ruy lopez|spanish opening", "Ruy Lopez"),
        (r"italian game", "Italian Game"), (r"english opening", "English Opening"),
        (r"r[eé]ti", "Réti Opening"), (r"gr[uü]nfeld", "Grünfeld Defense"),
        (r"slav", "Slav Defense"), (r"scandinavian", "Scandinavian Defense"),
        (r"dutch", "Dutch Defense"), (r"pirc", "Pirc Defense"),
        (r"ale[ck]hine", "Alekhine Defense"), (r"king'?s pawn", "King's Pawn Openings"),
        (r"vienna", "Vienna Game"), (r"petrov|russian game", "Petrov Defense"),
        (r"modern defense", "Modern Defense"),
    ]
    for pattern, family in families:
        if re.search(pattern, value, re.IGNORECASE):
            return family
    return re.split(r"\s+(?:Defense|Opening|Game|Variation|Attack|System|Line)\b", value, flags=re.IGNORECASE)[0].strip() or value


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
