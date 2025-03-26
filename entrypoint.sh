#!/bin/bash
set -e

# No need to activate virtual environment - using system Python

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U postgres; do
  sleep 1
done

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create a superuser if it does not exist
echo "Creating superuser..."
DJANGO_SUPERUSER_PASSWORD=admin DJANGO_SUPERUSER_EMAIL=admin@example.com DJANGO_SUPERUSER_USERNAME=admin python manage.py createsuperuser --noinput || echo "Superuser already exists."

# Load sample data
echo "Loading sample data..."
python manage.py load_glyphs
python manage.py load_sample_signs
python manage.py load_sample_phrases

# Start the development server
echo "Starting development server..."
python manage.py runserver 0.0.0.0:8000
