# Moss Garden

A persistent garden for slow, steady coding work. The API lives in `backend/`. The React screen lives in `frontend/`. FastAPI serves the built page.

## Local setup

Requires Python 3.12.3.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
copy backend\.env.example backend\.env
```

Set `DATABASE_URL` in `backend/.env` before running migrations. A local Postgres example:

```text
postgresql+psycopg://moss:moss@localhost:5432/moss_garden
```

Build the React garden:

```powershell
cd frontend
npm install
npm run build
cd ..
```

Apply migrations, start the app, and check health from `backend/`:

```powershell
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`GET http://127.0.0.1:8000/healthz` returns `{"status":"ok"}`. The health check does not open a database connection, so the process can start before Postgres is reachable. Migrations cannot.

Run tests:

```powershell
cd backend
python -m pytest
```

## Configuration

Secrets stay in environment variables. `backend/.env.example` lists every setting with empty secrets. Audio defaults to off. The local Backboard model is `openrouter` / `google/gemma-4-26b-a4b-it`, confirmed from `GET /models` on 2026-10-22. `AI_ENABLED` still defaults to false.

`DATABASE_URL` values that start with `postgresql://` or `postgres://` are rewritten to `postgresql+psycopg://`, which matches Render's connection string and the psycopg v3 driver.

## Render

`render.yaml` defines a free web service and a free Postgres database. The web service builds the root `Dockerfile`, runs `alembic upgrade head` each time the container starts, and uses `/healthz` as its health check. Free web services cannot use a pre-deploy command, so the migration is part of the start command.

A free Render web service spins down after 15 minutes without an inbound request. Render's own health probe does not count as that traffic. `.github/workflows/keep-alive.yml` requests `/healthz` every 10 minutes. After the first deploy, set the GitHub repository variable `RENDER_HEALTH_URL` to `https://<your-service>.onrender.com/healthz`. GitHub can start a scheduled run late, so a free instance can still sleep until the next successful ping. A paid Render plan is what stays up without a ping. See https://render.com/docs/free.

Render cron jobs have no free plan, so `.github/workflows/nightly-sync.yml` starts the nightly garden sync at 00:10 UTC. It sends `POST /api/jobs/nightly` with `Authorization: Bearer <SYNC_SECRET>`. The blueprint generates `SYNC_SECRET` on the web service. Copy that value from the Render dashboard into a GitHub repository secret named `SYNC_SECRET`. The workflow reuses `RENDER_HEALTH_URL` to find the service.

Local Docker:

```powershell
docker compose up --build
```

The API listens on port 8000 and reads `backend/.env`.

Free Render Postgres expires 30 days after creation, has no backups, and is limited to one free database per workspace. Upgrade the plan before that window if the garden should keep its data. See https://render.com/docs/free.

Set `BACKBOARD_API_KEY`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `ELEVENLABS_API_KEY` in the Render dashboard when those features exist. The blueprint marks them `sync: false`, so they are not stored in this file.

This milestone does not include a live deployment URL.
