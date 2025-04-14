# Base image with Python + Alpine
FROM python:3.13-alpine

# Set working directory in container
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev make

# Copy dependencies list and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Run Gunicorn in production
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:80", "run:app"]

