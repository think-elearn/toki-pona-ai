# AI-Powered Toki Pona Language Learning App

[![Build Status](https://github.com/think-elearn/toki-pona-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/think-elearn/toki-pona-ai/actions)
[![Dependabot Updates](https://github.com/think-elearn/toki-pona-ai/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/think-elearn/toki-pona-ai/actions/workflows/dependabot/dependabot-updates)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/think-elearn/toki-pona-ai/main.svg)](https://results.pre-commit.ci/latest/github/think-elearn/toki-pona-ai/main)
[![codecov](https://codecov.io/gh/think-elearn/toki-pona-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/think-elearn/toki-pona-ai)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This is an AI-powered Toki Pona language learning app based on prototypes created during ExamPro's 2025 GenAI Essentials bootcamp. See the original [bootcamp repository](https://github.com/dr-rompecabezas/free-genai-bootcamp-2025) for the projects that inspired this app.

## Pre-requisites

- Python 3.12
- PostgreSQL
- Docker and Docker Compose (optional)
- Git

## Setup Options

You can set up the application in two ways:

1. Using Docker (recommended)
2. Local setup

## Option 1: Using Docker (Recommended)

This is the easiest way to get started, as it will set up everything for you, including the database and ML dependencies.

### Step 1: Clone the repository

```bash
git clone https://github.com/think-elearn/toki-pona-ai.git
cd toki-pona-ai
```

### Step 2: Start Docker Compose

```bash
docker-compose -f compose.dev.yaml up --build
```

This will:

- Build the Docker image with all required dependencies
- Start PostgreSQL database
- Run Django migrations
- Load sample data from the static SVG files
- Start the development server

### Step 3: Access the application

The application will be available at <http://localhost:8000>

To access the admin dashboard, go to <http://localhost:8000/admin> and log in with:

- Username: admin
- Password: admin

## Option 2: Local Setup

### Step 1: Clone the repository

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
# Install ML-specific dependencies
pip install mediapipe cairosvg opencv-python pillow
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
DEBUG=True" > .env
```

### Step 6: Run migrations

```bash
python manage.py migrate
```

### Step 7: Load sample data

```bash
# Create an admin user
python manage.py createsuperuser

# Load sample glyphs from static SVG files
# This also generates the necessary PNG templates for the recognition system
python manage.py load_sample_glyphs
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
