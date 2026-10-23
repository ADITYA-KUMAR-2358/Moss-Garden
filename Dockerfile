# Build the garden page, then run the API that serves it.
FROM node:22-bookworm-slim AS frontend

WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12.3-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend /src/frontend/dist frontend/dist

WORKDIR /app/backend
EXPOSE 8000

# Render sets PORT. Local Docker uses 8000 when PORT is unset.
# Migrations run at start because free Render web services cannot use a pre-deploy command.
CMD ["sh", "-c", "set -e; if [ -n \"$DATABASE_URL\" ]; then alembic upgrade head; fi; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
