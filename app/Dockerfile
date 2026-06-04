FROM python:3.11-slim

# Set environment defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies if any are needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ .
COPY migrations/ ./migrations/
COPY alembic.ini .

EXPOSE 8000

# Run uvicorn server
CMD ["sh", "-c", "alembic upgrade head && python seed.py && python seed_live.py && uvicorn main:app --host 0.0.0.0 --port $PORT"]
