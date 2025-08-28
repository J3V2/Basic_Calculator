FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (gcc etc. only if needed for pip packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy application code
COPY . .

# Expose port (match gunicorn bind)
EXPOSE 8000

# Default command for production
CMD ["gunicorn", "api.app:app"]
