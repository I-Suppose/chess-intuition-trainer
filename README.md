# Chess Intuition Trainer

A web application for importing public Chess.com and Lichess games and turning the player's own turning points into chess training puzzles.

## What is implemented

- Supabase email/password sign-up and sign-in.
- Owner-scoped FastAPI endpoints using the signed-in Supabase user.
- Real public profile validation through the Chess.com Published Data API and Lichess API.
- Background game imports through Celery and Redis; latest 100 games per account on first import.
- PGN and game metadata storage in PostgreSQL, with duplicate prevention and newest-first game browsing.
- Stockfish UCI analysis of the connected player's decisions, processed newest game first in the background.
- Turning point classification and puzzles generated only from imported game positions; solutions use legal engine moves and verified close alternatives.
- Opening repertoire and move line summaries derived from the user's imported PGNs.
- Puzzle solving on a legal interactive chessboard, recorded attempts, solution line playback, and priority/category filters.
- Refresh, older-game import API, sync status, and account disconnect that preserves imported game history.
- Responsive dashboard, account connection, game library, and settings screens.
- Light and dark theme selection saved in the browser.
- Alembic migrations and Docker Compose development services, with Stockfish installed in the backend image.

Full application account deletion and advanced coach features from the PRD are not implemented. Puzzle positions are created from actual imported PGNs and Stockfish analysis; no general puzzle feed or sample positions are used.

## Start locally

1. Install Docker Desktop, Node.js 20+, and Python 3.12+ (or use the included containers for Python and Node).
2. Create a Supabase project and enable email/password authentication.
3. Copy `.env.example` to `.env` and set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY`. The public and server URLs should refer to the same Supabase project. Keep the service role key private.
4. From this directory, start the app:

   ```powershell
   Copy-Item .env.example .env
   # Edit .env and add your Supabase project values
   docker compose up --build
   ```

5. Open [http://localhost:3000](http://localhost:3000), create an account, then connect Chess.com or Lichess from **Accounts**.

The API is at [http://localhost:8000](http://localhost:8000), OpenAPI docs at [http://localhost:8000/docs](http://localhost:8000/docs), and health check at [http://localhost:8000/health](http://localhost:8000/health).

## Run the web and API outside Docker

Start PostgreSQL and Redis, configure `.env`, and run. The Compose API and worker override the host-only database and Redis URLs with the internal `db` and `redis` service addresses; the browser still uses `http://localhost:8000/api/v1` by default.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

In a second backend terminal, start the worker:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker --loglevel=INFO --concurrency=2
```

In another terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` to the API base URL with `/api/v1` appended. The frontend is a Vite-built React single-page app using React Router; its `VITE_*` settings are embedded at build time in Docker, so rebuild the frontend container after changing them.

## Deploy to Fly.io

The repository has separate `frontend/` and `backend/` folders, so Fly cannot detect an app from the repository root without an explicit Dockerfile. The root `Dockerfile` builds the React site and FastAPI service into one image; FastAPI serves the built site and API on the same origin. The `web` and Celery `worker` process groups are configured in `fly.toml`.

1. Install `flyctl` and sign in with `fly auth login`.
2. In `fly.toml`, replace `chess-intuition-trainer-change-me` with an app name that is available. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` under `[build.args]` to the public URL and anon key for your Supabase project. These Vite values are included in the browser build; never put the Supabase service-role key there.
3. From the repository root, create the Fly app without deploying yet:

   ```powershell
   fly launch --no-deploy --name your-unique-chess-trainer-name
   ```

   Choose not to create an additional database if prompted; the app needs PostgreSQL and Redis configured as described next.
4. Create or select a Fly Managed Postgres cluster and attach it to the app. Attaching sets `DATABASE_URL` for the app:

   ```powershell
   fly mpg create
   fly mpg attach YOUR_CLUSTER_ID --app your-unique-chess-trainer-name
   ```

5. Create an Upstash Redis service from Fly's Redis section, then set its private connection URL and the Supabase server credentials as Fly secrets:

   ```powershell
   fly secrets set REDIS_URL="YOUR_PRIVATE_REDIS_URL" SUPABASE_URL="YOUR_SUPABASE_URL" SUPABASE_ANON_KEY="YOUR_SUPABASE_ANON_KEY" SUPABASE_SERVICE_ROLE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY" --app your-unique-chess-trainer-name
   ```

6. Deploy from the repository root:

   ```powershell
   fly deploy --app your-unique-chess-trainer-name
   fly status --app your-unique-chess-trainer-name
   fly logs --app your-unique-chess-trainer-name
   ```

The Fly release command runs the database migrations before the web and worker processes start. The Dockerfile and Fly configuration are at the repository root so `fly launch` and `fly deploy` see them.

## Import behavior and configuration

- Chess.com imports discover monthly archives newest-first and request only enough games to reach the configured limit.
- Lichess imports use the official game export endpoint, one request per sync, with bounded retry for rate limits.
- Games with unknown dates keep a null date and appear after dated games; the application never invents a date.
- `POST /api/v1/games/import-older?account_id=<uuid>` requests the next older page for a connected account.
- `POST /api/v1/accounts/{account_id}/sync` queues a refresh. Background work requires Redis and a running Celery worker.
- `INITIAL_GAME_IMPORT_LIMIT` defaults to 100. Pending games are analyzed automatically after import and when the API starts. The fast Stockfish scan runs on each user decision; positions that look important receive the configured deeper analysis.
- `STOCKFISH_SCAN_TIME_LIMIT` controls the quick scan per decision. `STOCKFISH_DEPTH` and `STOCKFISH_TIME_LIMIT` control deeper candidate analysis. Set `STOCKFISH_PATH` if Stockfish is not on the executable path.
- `/api/v1/openings` summarizes opening families and the first 12 half-moves from the actual PGNs.
- `/api/v1/games/{game_id}/analysis` returns evaluated user decision positions. `/api/v1/puzzles` lists puzzles in category priority order, with newer games first within a category.
- Puzzle attempts are checked against legal moves and the engine's best move plus alternatives within 0.25 pawns. The solution is available after an attempt.

See `.env.example` for the complete configuration list. Never commit `.env` or place the Supabase service role key in a `VITE_` variable; Vite exposes those values to the browser.
