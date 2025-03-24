# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Collect static files with dummy database for build
ENV DATABASE_URL=sqlite:///tmp/dummy-db.sqlite3
ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV SECRET_KEY=build-time-only-secret-key-not-used-in-production
ENV ALLOWED_HOSTS="localhost,127.0.0.1,[::1],toki-pona-ai.fly.dev"
ENV AWS_ACCESS_KEY_ID=build-time-dummy-key
ENV AWS_SECRET_ACCESS_KEY=build-time-dummy-secret
ENV BUCKET_NAME=build-time-dummy-bucket
ENV AWS_REGION=us-east-1
ENV AWS_ENDPOINT_URL_S3=https://dummy-endpoint
ENV REDIS_URL=redis://localhost:6379/0
RUN python manage.py collectstatic --noinput

# Migrations will be run by the release command in fly.toml

# Set up entry point
EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=config.settings.production
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
