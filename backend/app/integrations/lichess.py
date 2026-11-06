from datetime import datetime, timezone
import io
import chess.pgn
import httpx
from app.integrations.errors import RateLimitError
from app.services.pgn_processor import normalize_game_result


async def fetch_games(username: str, limit: int = 100, before: int | None = None):
    headers = {"Accept": "application/x-chess-pgn", "User-Agent": "ChessIntuitionTrainer/0.1"}
    async with httpx.AsyncClient(timeout=60, headers=headers) as client:
        profile = await client.get(f"https://lichess.org/api/user/{username}")
        if profile.status_code == 429:
            raise RateLimitError(int(profile.headers.get("Retry-After", "60")))
        if profile.status_code == 404:
            raise ValueError("Lichess username was not found.")
        profile.raise_for_status()
        results = []
        cursor = before
        while len(results) < limit:
            batch_limit = min(300, limit - len(results))
            params = {"max": batch_limit, "moves": "true", "opening": "true", "clocks": "false", "evals": "false", "pgnInJson": "false"}
            if cursor is not None:
                params["before"] = cursor
            response = await client.get(f"https://lichess.org/api/games/user/{username}", params=params)
            if response.status_code == 429:
                raise RateLimitError(int(response.headers.get("Retry-After", "60")))
            response.raise_for_status()
            batch = parse_export(response.text, username)
            if not batch:
                break
            results.extend(batch)
            dates = [game["played_at"] for game in batch if game.get("played_at")]
            if len(batch) < batch_limit or not dates:
                break
            next_cursor = int(min(dates).timestamp() * 1000) - 1
            if cursor is not None and next_cursor >= cursor:
                break
            cursor = next_cursor
        return results[:limit]


def parse_export(text: str, username: str):
    games = []
    stream = io.StringIO(text)
    while game := chess.pgn.read_game(stream):
        h = game.headers
        uid = h.get("Site", "")
        def date_value():
            raw = h.get("UTCDate") or h.get("Date")
            stamp = h.get("UTCTime") or "00:00:00"
            try:
                return datetime.strptime(f"{raw} {stamp}", "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return None
        white, black = h.get("White"), h.get("Black")
        colour = "white" if (white or "").casefold() == username.casefold() else "black"
        result = h.get("Result")
        user_result = normalize_game_result(result, colour)
        games.append({"id": uid or h.get("GameId") or h.get("UTCDate", "unknown") + ":" + (white or "") + ":" + (black or ""),
                      "url": uid or None, "white": white, "black": black, "user_colour": colour,
                      "opponent": black if colour == "white" else white, "result": user_result, "played_at": date_value(),
                      "time_control": h.get("TimeControl"), "opening": h.get("Opening"), "pgn": game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False))})
    return games
