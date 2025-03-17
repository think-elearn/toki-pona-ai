FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy project
COPY . .

# Collect static files with dummy database for build
ENV DATABASE_URL=sqlite:///tmp/dummy-db.sqlite3
RUN python manage.py collectstatic --noinput

# Migrations will be run by the release command in fly.toml

# Set up entry point
EXPOSE 8000
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
