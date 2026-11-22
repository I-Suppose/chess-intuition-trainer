# Chess Intuition Trainer

A React and FastAPI application for importing public Chess.com and Lichess games and turning the player's own turning points into chess training puzzles. Accounts and application data are stored in MySQL; authentication is handled by the FastAPI backend.

## Start locally with MySQL

1. Ensure MySQL Server is running on `127.0.0.1:3306`. MySQL Workbench is a client; the application connects to the MySQL Server service.
2. In Workbench, create the application's database once:

   ```sql
   CREATE DATABASE chess_trainer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. Copy `.env.example` to `.env`. Set the MySQL username and password in both `DATABASE_URL` and `DATABASE_URL_DOCKER`. `DATABASE_URL` is for running Python on Windows; Docker containers use `DATABASE_URL_DOCKER` and reach the Windows host through `host.docker.internal`. Set `JWT_SECRET_KEY` to a long random value. Keep `.env` private.
4. Start the app:

   ```powershell
   docker compose up --build
   ```

5. Open [http://localhost:3000](http://localhost:3000), create an account, and connect Chess.com or Lichess from **Accounts**.

Redis is started by Compose. MySQL must be running outside Compose. The API is at [http://localhost:8000](http://localhost:8000), OpenAPI docs at [http://localhost:8000/docs](http://localhost:8000/docs), and health check at [http://localhost:8000/health](http://localhost:8000/health).

## Run web and API outside Docker

Configure `DATABASE_URL` in `.env` for your local MySQL Server, then install dependencies and apply migrations:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Run a Redis server and a Celery worker in another backend terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker --loglevel=INFO --concurrency=2
```

Run the frontend in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite frontend uses `VITE_API_URL` as its API base URL. Account creation and sign-in use the backend `/auth/register` and `/auth/login` endpoints; password hashes and application records are stored in MySQL.

## Existing accounts and data

Supabase passwords cannot be copied into this app because their password hashes are not available to it. Users need to create a new account after the switch. Existing PostgreSQL game data is not copied automatically; retain its database backup and import the public games again after creating the new account. The MySQL migration creates the schema and does not transfer or delete the old PostgreSQL database.

## Deploy to Fly.io

The root Dockerfile builds the React site and FastAPI backend into one image. Set Fly secrets for a MySQL server reachable from Fly and Redis before deployment:

```sh
fly secrets set DATABASE_URL='mysql+pymysql://USER:PASSWORD@MYSQL_HOST:3306/chess_trainer?charset=utf8mb4' JWT_SECRET_KEY='LONG_RANDOM_SECRET' REDIS_URL='YOUR_PRIVATE_REDIS_URL' --app chess-intuition-trainer
fly deploy --app chess-intuition-trainer
```

The MySQL database must be hosted or otherwise reachable from Fly. `localhost` on a Fly machine refers to that machine, not the MySQL Server on your personal computer. `DATABASE_URL` may use `mysql+pymysql://` or a provider's standard `mysql://` scheme. Do not put database credentials or JWT secrets in Vite build variables. Fly's release command runs Alembic migrations before starting the app.

## Deploy the frontend to Vercel

This repository keeps the React/Vite frontend in `frontend/` and the FastAPI API in `backend/`. The root and frontend Vercel configuration files both install frontend development dependencies explicitly, run the npm build script, and publish the Vite `dist` output. For a standard Vercel project, keep **Root Directory** set to the repository root (`.`). If the project's Root Directory is set to `frontend`, Vercel uses `frontend/vercel.json` instead.

Add `VITE_API_URL` in Vercel's project environment variables with the public API base, for example `https://chess-intuition-trainer.fly.dev/api/v1`, then redeploy. The API must be running separately (for example on Fly.io); Vercel is serving the static React frontend. Add the Vercel site's exact `https://...vercel.app` origin to the backend's `CORS_ORIGINS` setting so browser API requests are allowed. Vite embeds `VITE_API_URL` during the build, so changing it requires a redeploy.

## Import and analysis configuration

- Chess.com imports discover monthly archives newest-first and request only enough games to reach the configured limit.
- Lichess imports use the official game export endpoint, one request per sync, with bounded retry for rate limits.
- `INITIAL_GAME_IMPORT_LIMIT` defaults to 100. Background work requires Redis and a running Celery worker.
- `STOCKFISH_SCAN_TIME_LIMIT` controls the quick scan per decision. `STOCKFISH_DEPTH` and `STOCKFISH_TIME_LIMIT` control deeper candidate analysis. Set `STOCKFISH_PATH` if Stockfish is not on the executable path.
- `/api/v1/openings` summarizes opening families and move lines from imported PGNs.
- Puzzle positions are generated from actual imported games and engine analysis.

See `.env.example` for the configuration names. Do not commit `.env`.
