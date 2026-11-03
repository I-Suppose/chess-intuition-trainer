from datetime import datetime, timezone
import httpx
from app.integrations.errors import RateLimitError

BASE = "https://api.chess.com/pub"
HEADERS = {"User-Agent": "ChessIntuitionTrainer/0.1 (public game importer)"}


async def fetch_games(username: str, limit: int = 100, before: datetime | None = None):
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        profile = await client.get(f"{BASE}/player/{username}")
        if profile.status_code == 429:
            raise RateLimitError(int(profile.headers.get("Retry-After", "30")))
        if profile.status_code == 404:
            raise ValueError("Chess.com username was not found.")
        profile.raise_for_status()
        archives_res = await client.get(f"{BASE}/player/{username}/games/archives")
        if archives_res.status_code == 429:
            raise RateLimitError(int(archives_res.headers.get("Retry-After", "30")))
        archives_res.raise_for_status()
        archives = archives_res.json().get("archives", [])
        results = []
        for archive in reversed(archives):
            response = await client.get(archive)
            if response.status_code == 429:
                raise RateLimitError(int(response.headers.get("Retry-After", "30")))
            if response.status_code == 404:
                continue
            response.raise_for_status()
            month_games = response.json().get("games", [])
            for game in reversed(month_games):
                end = game.get("end_time")
                played = datetime.fromtimestamp(end, timezone.utc) if end else None
                if before and played and played >= before:
                    continue
                results.append(normalize_game(game, username, played))
                if len(results) >= limit:
                    return results
        return results


def normalize_game(game, username, played):
    white, black = game.get("white", {}), game.get("black", {})
    white_name, black_name = white.get("username"), black.get("username")
    user_colour = "white" if (white_name or "").casefold() == username.casefold() else "black"
    eco = game.get("eco")
    opening = eco.rsplit("/", 1)[-1].replace("-", " ") if isinstance(eco, str) and eco.startswith("http") else eco
    return {"id": game.get("url", game.get("uuid", game.get("pgn", ""))), "url": game.get("url"), "white": white_name, "black": black_name,
            "user_colour": user_colour, "opponent": black_name if user_colour == "white" else white_name, "result": white.get("result") if user_colour == "white" else black.get("result"),
            "played_at": played, "time_control": game.get("time_control"), "opening": opening, "pgn": game.get("pgn", "")}
