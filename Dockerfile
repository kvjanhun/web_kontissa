# Stage 1: Build frontend
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/ ./frontend/
RUN cd frontend && npm ci && npm run build
# Output: /src/frontend/.output/public/

# Stage 2: Python runtime
FROM python:3.13-alpine
WORKDIR /app
RUN apk add --no-cache gcc musl-dev libffi-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY scripts/ ./scripts/
# Seed source for the one-off home-content migration (scripts/seed_home_content.py).
# The rest of frontend/ is not in the runtime image, so copy this file explicitly.
COPY frontend/locales/home-content.snapshot.json ./frontend/locales/home-content.snapshot.json
COPY run.py .
COPY --from=frontend /src/frontend/.output/public/ ./app/static/dist/

RUN addgroup -S webapp && adduser -S webapp -G webapp
RUN mkdir -p /app/data && chown -R webapp:webapp /app/data

USER webapp

# --timeout 120 / --graceful-timeout 30: a slow request (cold-start index reload
# under load) must not get the sync worker SIGKILLed mid-request — that turns
# transient slowness into hard 500/502s at the edge. The compose `web` service
# overrides this command; keep the two in sync.
CMD ["gunicorn", "--preload", "-w", "2", "--timeout", "120", "--graceful-timeout", "30", "-b", "0.0.0.0:80", "run:app"]
