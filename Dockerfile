# Stage 1: Build frontend
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend-nuxt/ ./frontend-nuxt/
RUN cd frontend-nuxt && npm ci && npm run build
# Output: /src/frontend-nuxt/.output/public/

# Stage 2: Python runtime
FROM python:3.13-alpine
WORKDIR /app
RUN apk add --no-cache gcc musl-dev libffi-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY run.py .
COPY --from=frontend /src/frontend-nuxt/.output/public/ ./app/static/dist/
CMD ["gunicorn", "--preload", "-w", "2", "-b", "0.0.0.0:80", "run:app"]
