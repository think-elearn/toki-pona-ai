#!/bin/bash
set -e

# No need to activate virtual environment - using system Python

# Print environment variables for debugging
echo "Checking environment variables..."
echo "ANTHROPIC_API_KEY is ${ANTHROPIC_API_KEY:+set (value hidden)}"
echo "YOUTUBE_API_KEY is ${YOUTUBE_API_KEY:+set (value hidden)}"

# Create .env file with the necessary environment variables
echo "Creating .env file for Django..."
cat > .env << EOL
DATABASE_URL=postgres://postgres:postgres@db:5432/toki_pona_db
SECRET_KEY=${SECRET_KEY:-dev-key-replace-in-production}
DEBUG=${DEBUG:-True}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
YOUTUBE_API_KEY=${YOUTUBE_API_KEY:-}
USE_S3_STORAGE=${USE_S3_STORAGE:-false}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
AWS_STORAGE_BUCKET_NAME=${AWS_STORAGE_BUCKET_NAME:-}
AWS_S3_REGION_NAME=${AWS_S3_REGION_NAME:-}
AWS_S3_ENDPOINT_URL=${AWS_S3_ENDPOINT_URL:-}
EOL

# Check if API keys are missing
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "WARNING: ANTHROPIC_API_KEY is not set. AI tutor functionality will not work correctly."
fi

if [ -z "$YOUTUBE_API_KEY" ]; then
  echo "WARNING: YOUTUBE_API_KEY is not set. Video search functionality will not work correctly."
fi

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

# Handle sign language videos
if [ "${DOWNLOAD_SIGN_VIDEOS}" = "true" ]; then
  echo "Downloading sign language videos..."
  if [ -n "${VIDEO_SOURCE_URL}" ]; then
    # Download from specified URL if provided
    python manage.py download_sign_videos --source url --url "${VIDEO_SOURCE_URL}"
  else
    # Otherwise try to download from S3 if configured
    python manage.py download_sign_videos
  fi
fi

# Process sign videos to extract landmarks
echo "Processing sign videos..."
python manage.py process_sign_videos --download

# Start the development server
echo "Starting development server..."
python manage.py runserver 0.0.0.0:8000
