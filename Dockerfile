FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations and load initial data
CMD ["sh", "-c", "python manage.py migrate && python manage.py load_sample_phrases && python manage.py load_sample_glyphs && python manage.py load_sample_signs && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]

EXPOSE 8000
