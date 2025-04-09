#!/bin/bash
set -e

echo "Starting production entrypoint script..."

# Check if required environment variables are set
if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL is not set. Exiting."
  exit 1
fi

# Print environment variables status
echo "Checking environment variables..."
echo "DATABASE_URL is set (value hidden)"
echo "REDIS_URL is ${REDIS_URL:+set (value hidden)}"
echo "ANTHROPIC_API_KEY is ${ANTHROPIC_API_KEY:+set (value hidden)}"
echo "YOUTUBE_API_KEY is ${YOUTUBE_API_KEY:+set (value hidden)}"

# Check if database connection check is disabled
if [ "${DATABASE_CHECK_DISABLED}" = "true" ]; then
  echo "Database connection check is disabled by environment variable"
else
  # Extract database host and port from DATABASE_URL
  # Format example: postgres://username:password@hostname:port/database
  if [[ $DATABASE_URL =~ postgres://[^:]+:[^@]+@([^:]+):([0-9]+)/ ]]; then
    DB_HOST=${BASH_REMATCH[1]}
    DB_PORT=${BASH_REMATCH[2]}
    echo "Extracted database host: $DB_HOST"
    echo "Extracted database port: $DB_PORT"

    # Check if this is the release command (the script is called with arguments)
    if [ $# -eq 0 ]; then
      # Wait for PostgreSQL to be ready with a timeout
      echo "Waiting for PostgreSQL database to be ready..."
      max_attempts=5
      counter=0

      until pg_isready -h $DB_HOST -p $DB_PORT; do
        counter=$((counter + 1))
        if [ $counter -eq $max_attempts ]; then
          echo "WARNING: Database connection check timed out, but continuing startup..."
          break
        fi
        echo "Waiting for database connection... (attempt $counter/$max_attempts)"
        sleep 2
      done

      if [ $counter -lt $max_attempts ]; then
        echo "Database connection successful!"
      fi
    else
      echo "Running as release command - skipping lengthy database connection check"
    fi
  else
    echo "WARNING: Could not extract host and port from DATABASE_URL. Connection check will be skipped."
  fi
fi

# Only run collectstatic and migrations in the app process group
if [ "$FLY_PROCESS_GROUP" = "app" ]; then
  # Run collectstatic
  echo "Collecting static files..."
  python manage.py collectstatic --noinput || echo "WARNING: Collectstatic failed, but continuing startup anyway"

  # Run migrations
  echo "Running migrations..."
  python manage.py migrate --noinput || echo "WARNING: Migration failed, but continuing startup anyway"
elif [[ "$@" == *"--migrate"* ]]; then
  # If explicitly requested via --migrate flag
  echo "Running migrations as explicitly requested..."
  python manage.py migrate --noinput || echo "WARNING: Migration failed, but continuing startup anyway"
else
  echo "Skipping collectstatic and migrations in non-app process or when not explicitly requested"
fi

# Check for FLY_PROCESS_GROUP to determine which process to start
if [ -n "$FLY_PROCESS_GROUP" ]; then
  case "$FLY_PROCESS_GROUP" in
    app)
      echo "Starting Daphne server for web application..."
      exec daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application
      ;;
    worker)
      echo "Starting Celery worker..."
      exec celery -A config worker --loglevel=info
      ;;
    beat)
      echo "Starting Celery beat..."
      exec celery -A config beat --loglevel=info
      ;;
    *)
      echo "Unknown process group: $FLY_PROCESS_GROUP. Starting default process (Daphne)..."
      exec daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application
      ;;
  esac
# Default command if no process group specified or for local dev
elif [ $# -eq 0 ]; then
  echo "No process group set, starting Daphne server..."
  exec daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application
else
  echo "Running command: $@"
  exec "$@"
fi
