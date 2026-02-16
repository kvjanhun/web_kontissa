# Base image with Python + Alpine
FROM python:3.13-alpine

# Set working directory in container
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev make curl

# Download Tailwind CSS standalone CLI
RUN curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 \
    && chmod +x tailwindcss-linux-x64 \
    && mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss

# Copy dependencies list and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Build Tailwind CSS (minified)
RUN tailwindcss -i app/static/assets/input.css -o app/static/assets/style.css --minify

# Run Gunicorn in production
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:80", "run:app"]
