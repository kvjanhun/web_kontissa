FROM python:3.11-alpine

# Install system dependencies
RUN apk add --no-cache build-base libffi-dev

# Set working dir
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app/ /app/

# Expose port 80 and run
CMD ["python", "main.py"]
EXPOSE 80
