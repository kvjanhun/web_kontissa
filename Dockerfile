# Stage 1: Build frontend
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/ ./frontend/
RUN cd frontend && npm ci && npm run build
# Output: /src/frontend/.output/public/

# Stage 2: Python runtime
FROM python:3.13-alpine
WORKDIR /app
COPY requirements.txt .
RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev \
 && pip install --no-cache-dir -r requirements.txt \
 && apk del .build-deps
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY run.py .
COPY --from=frontend /src/frontend/.output/public/ ./app/static/dist/

RUN addgroup -S webapp && adduser -S webapp -G webapp
RUN mkdir -p /app/data && chown -R webapp:webapp /app/data

USER webapp

CMD ["gunicorn", "--preload", "-w", "2", "-b", "0.0.0.0:80", "run:app"]
