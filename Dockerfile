FROM python:3.11-slim

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

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations and load initial data
RUN mkdir -p /app/media

# Set up entry point
EXPOSE 8000
CMD gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
