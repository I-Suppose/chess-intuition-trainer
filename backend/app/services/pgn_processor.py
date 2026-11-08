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


def normalize_time_control(value: str | None) -> str | None:
    """Format the base clock in minutes while retaining the increment in seconds."""
    if not value:
        return value
    match = re.fullmatch(r"\s*(\d+)(?:\+(\d+))?\s*", value)
    if not match:
        return value
    seconds = int(match.group(1))
    minutes = seconds / 60
    base = str(int(minutes)) if minutes.is_integer() else f"{minutes:g}"
    increment = match.group(2) or "0"
    return f"{base}+{increment}"


def normalize_game_result(result: str | None, user_colour: str | None) -> str:
    """Convert platform-specific termination labels into the player's outcome."""
    value = (result or "").strip().lower().replace(" ", "")
    if value in ("win", "won"):
        return "win"
    if value in ("loss", "lost", "lose", "checkmated", "resigned", "timeout", "abandoned"):
        return "loss"
    if value == "1-0":
        return "win" if user_colour == "white" else "loss"
    if value == "0-1":
        return "win" if user_colour == "black" else "loss"
    return "draw"


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
