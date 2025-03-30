# Toki Pona AI: Interactive Tutor, Listening, Writing and Signing

[![Build Status](https://github.com/think-elearn/toki-pona-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/think-elearn/toki-pona-ai/actions)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/think-elearn/toki-pona-ai/main.svg)](https://results.pre-commit.ci/latest/github/think-elearn/toki-pona-ai/main)
[![codecov](https://codecov.io/gh/think-elearn/toki-pona-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/think-elearn/toki-pona-ai)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Toki Pona AI is a comprehensive language learning platform for Toki Pona - a minimalist constructed language with only about 120 core words. The application features four interactive learning modules:

- **Tutor Module**: AI-powered personalized learning sessions
- **Listening Module**: Audio recognition exercises to improve comprehension
- **Writing Module**: Practice for Sitelen Pona (the logographic writing system)
- **Signing Module**: Interactive lessons for Luka Pona sign language

This project was originally developed as a final assignment for ExamPro's 2025 applied GenAI bootcamp, evolving from Streamlit and CLI-based prototypes. For the earlier versions, see the original [bootcamp repository](https://github.com/dr-rompecabezas/free-genai-bootcamp-2025).

## Pre-requisites

- Git
- Python 3.12
- Docker and Docker Compose (recommended for easier setup)
- Anthropic API key (required for the tutor module)
- YouTube API key (required for the tutor module)

For the non-Docker setup, you will also need to install the following:

### System dependencies

- PostgreSQL 15 with pgvector extension
- Redis (for caching and background tasks)

### System libraries for ML and image processing

- OpenCV dependencies (libgl1-mesa-glx, libglib2.0-0, libsm6, libxrender1, libxext6)
- SVG processing dependencies (libcairo2-dev, pkg-config, python3-dev)
- Build essentials and PostgreSQL development libraries (build-essential, libpq-dev)

## Setup Options

You can set up the application in two ways:

1. Using Docker (recommended)
2. Local setup

## Option 1: Using Docker (Recommended)

This is the easiest way to get started, as it will set up everything for you, including the database and ML dependencies.

### Step 1: Clone the repository for Docker setup

```bash
git clone https://github.com/think-elearn/toki-pona-ai.git
cd toki-pona-ai
```

### Step 2: Start Docker Compose with your API keys

Both the Anthropic API key and YouTube API key are required for the tutor module functionality. To start the application with your API keys:

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key YOUTUBE_API_KEY=your_youtube_api_key docker compose -f compose.dev.yaml up --build
```

This will:

- Build the Docker image with all required dependencies
- Configure the application with your API keys
- Start PostgreSQL database (with health check to ensure it's ready)
- Run Django migrations
- Create an admin user automatically
- Load data for all apps (glyphs, signs, phrases)
- Download required ML models
- Create all necessary media directories
- Start the development server

The setup process is fully automated and will ensure the application is 100% functional once started.

If you need to restart the application later, you can use:

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key YOUTUBE_API_KEY=your_youtube_api_key docker compose -f compose.dev.yaml up
```

This approach avoids storing your API key in any files, keeping it secure and preventing accidental commits to version control.

### Step 3: Access the application

The application will be available at <http://localhost:8000>

To access the admin dashboard, go to <http://localhost:8000/admin> and log in with:

- Username: admin
- Password: admin

## Option 2: Local Setup

### Step 1: Clone the repository for local setup

```bash
git clone https://github.com/think-elearn/toki-pona-ai.git
cd toki-pona-ai
```

### Step 2: Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
pip install -e ".[dev]"
```

### Step 4: Set up PostgreSQL

Create a PostgreSQL database:

```bash
psql -U postgres
CREATE DATABASE toki_pona_db;
\q
```

### Step 5: Create .env file

Create a `.env` file in the project root:

```bash
echo "DATABASE_URL=postgres://postgres:postgres@localhost:5432/toki_pona_db
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
ANTROPIC_API_KEY=your_anthropic_api_key
DEBUG=True" > .env
```

### Step 6: Run migrations

```bash
python manage.py migrate
```

### Step 7: Load data

```bash
# Create an admin user
python manage.py createsuperuser

# Load glyphs from static SVG files
# This creates glyph records in the database, generates PNG templates for recognition,
# and automatically sets up all necessary directories in the media folder
python manage.py load_glyphs

# Load sample signs and phrases
python manage.py load_sample_signs
python manage.py load_sample_phrases
```

### Step 8: Run the development server

```bash
python manage.py runserver
```

### Step 9: Access the application

The application will be available at <http://localhost:8000>

## Using the Writing Practice Module

1. Log in to the application
2. Navigate to the Writing Practice module
3. Select a glyph to practice
4. Use the drawing canvas to practice writing the glyph
5. Click "Check Drawing" to get feedback on your writing

## Troubleshooting

### MediaPipe Installation Issues

If you encounter issues installing MediaPipe:

```bash
# For Linux
apt-get install -y libgl1-mesa-glx libglib2.0-0

# For macOS
brew install glib
```

### SVG Processing Issues

If you encounter issues with CairoSVG:

```bash
# For Linux
apt-get install -y libcairo2-dev pkg-config python3-dev

# For macOS
brew install cairo pkg-config
```

### Database Connection Issues

If you encounter database connection issues:

1. Check your PostgreSQL service is running
2. Verify your .env file has the correct DATABASE_URL
3. Make sure the database user has the necessary permissions

### Writing App Issues

If you encounter issues with the writing recognition feature:

1. Make sure you've run `python manage.py load_glyphs` to create the necessary templates
2. Check that the MediaPipe model was downloaded successfully to `media/ml_models/mobilenet_v3_small.tflite`
3. Verify that template images exist in `media/templates/`
4. If you see "No templates found" in the logs, re-run the `load_glyphs` command
5. Check browser console for any JavaScript errors

## Deployment to Production with Fly.io

The application is configured for deployment to Fly.io using the following steps:

1. Install flyctl: <https://fly.io/docs/hands-on/install-flyctl/>

2. Login to Fly.io

    ```bash
    fly auth login
    ```

3. Launch the app (first time only)

    ```bash
    fly launch --dockerfile Dockerfile.prod
    ```

4. Set the required environment variables

    ```bash
    # Generate a secure secret key
    SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')

    fly secrets set \
    SECRET_KEY="${SECRET_KEY}" \
    DEBUG="False" \
    ALLOWED_HOSTS="your-app-name.fly.dev,localhost,127.0.0.1,[::1]" \
    DATABASE_URL="your-postgres-connection-string" \
    ACCOUNT_ALLOW_REGISTRATION="True" \
    AWS_ACCESS_KEY_ID="your-s3-access-key" \
    AWS_SECRET_ACCESS_KEY="your-s3-secret-key" \
    BUCKET_NAME="your-s3-bucket-name" \
    AWS_REGION="your-s3-region" \
    AWS_ENDPOINT_URL_S3="https://your-s3-endpoint-url" \
    REDIS_URL="redis://your-redis-url:6379" \
    ANTHROPIC_API_KEY="your-anthropic-api-key" \
    YOUTUBE_API_KEY="your-youtube-api-key"
    ```

5. Deploy updates

    ```bash
    fly deploy
    ```

6. (Optional) Load sample data

    For a new deployment, you may want to load initial data:

    ```bash
    # Connect to the running app
    fly ssh console

    # Run data loading commands
    cd /app
    python manage.py load_glyphs
    python manage.py load_sample_signs
    python manage.py load_sample_phrases

    # Exit the console
    exit
    ```

## Next Steps

After setting up the application, you can:

1. Add more content to the database using the Django admin
2. Create user accounts for your learners
3. Customize the appearance and behavior of the application
4. Deploy the application to a production environment

## Further Resources

- [Toki Pona Official Website](https://tokipona.org/)
- [Django Documentation](https://docs.djangoproject.com/)
- [MediaPipe Documentation](https://developers.google.com/mediapipe)
- [Fly.io Documentation](https://fly.io/docs/)
