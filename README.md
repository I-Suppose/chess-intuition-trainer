# Chess Intuition Trainer

A web application for importing public Chess.com and Lichess games into a personal training library. This first implementation establishes the sign-in, account connection, import, storage, and game browsing milestone from the product requirements.

## What is implemented

- Supabase email/password sign-up and sign-in.
- Owner-scoped FastAPI endpoints using the signed-in Supabase user.
- Real public profile validation through the Chess.com Published Data API and Lichess API.
- Background game imports through Celery and Redis; latest 100 games per account on first import.
- PGN and game metadata storage in PostgreSQL, with duplicate prevention and newest-first game browsing.
- Refresh, older-game import API, sync status, and account disconnect that preserves imported game history.
- Responsive dashboard, account connection, game library, and settings screens.
- Alembic migration and Docker Compose development services.

Stockfish analysis, move classification, puzzle generation/solving, puzzle attempt tracking, and full account deletion are not implemented yet. The puzzle page intentionally reports this state and does not show fabricated analysis. The attached PRD remains the source for those next phases.

## Start locally

1. Install Docker Desktop, Node.js 20+, and Python 3.12+ (or use the included containers for Python and Node).
2. Create a Supabase project and enable email/password authentication.
3. Copy `.env.example` to `.env` and set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_ANON_KEY`. The public and server URLs should refer to the same Supabase project. Keep the service role key private.
4. From this directory, start the app:

   ```powershell
   Copy-Item .env.example .env
   # Edit .env and add your Supabase project values
   docker compose up --build
   ```

5. Open [http://localhost:3000](http://localhost:3000), create an account, then connect Chess.com or Lichess from **Accounts**.

The API is at [http://localhost:8000](http://localhost:8000), OpenAPI docs at [http://localhost:8000/docs](http://localhost:8000/docs), and health check at [http://localhost:8000/health](http://localhost:8000/health).

## Run the web and API outside Docker

Start PostgreSQL and Redis, configure `.env`, and run:

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

Set `NEXT_PUBLIC_API_URL` to the API base URL with `/api/v1` appended. The frontend Supabase variables are embedded at build time in Docker, so rebuild the frontend container after changing them.

## Import behavior and configuration

- Chess.com imports discover monthly archives newest-first and request only enough games to reach the configured limit.
- Lichess imports use the official game export endpoint, one request per sync, with bounded retry for rate limits.
- Games with unknown dates keep a null date and appear after dated games; the application never invents a date.
- `POST /api/v1/games/import-older?account_id=<uuid>` requests the next older page for a connected account.
- `POST /api/v1/accounts/{account_id}/sync` queues a refresh. Background work requires Redis and a running Celery worker.
- `INITIAL_GAME_IMPORT_LIMIT` defaults to 100. Stockfish settings in `.env.example` are reserved for the analysis phase.

See `.env.example` for the complete configuration list. Never commit `.env` or place the Supabase service role key in a `NEXT_PUBLIC_` variable.
