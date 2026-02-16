# Stage 1: Build frontend
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/ ./frontend/
RUN cd frontend && npm ci && npm run build
# Output: /src/app/static/dist/

# Stage 2: Python runtime
FROM python:3.13-alpine
WORKDIR /app
RUN apk add --no-cache gcc musl-dev libffi-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY run.py .
COPY --from=frontend /src/app/static/dist/ ./app/static/dist/
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:80", "run:app"]
