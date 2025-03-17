# AI-Powered Toki Pona Language Learning App

[![Build Status](https://github.com/think-elearn/toki-pona-ai/actions/workflows/test.yml/badge.svg)](https://github.com/think-elearn/toki-pona-ai/actions)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/think-elearn/toki-pona-ai/main.svg)](https://results.pre-commit.ci/latest/github/think-elearn/toki-pona-ai/main)
[![codecov](https://codecov.io/gh/think-elearn/toki-pona-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/think-elearn/toki-pona-ai)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This is an AI-powered Toki Pona language learning app based on prototypes created during ExamPro's 2025 GenAI Essentials bootcamp. See the original [bootcamp repository](https://github.com/dr-rompecabezas/free-genai-bootcamp-2025) for the projects that inspired this app.

## Pre-requisites

- Python 3.12
- PostgreSQL
- pre-commit

## Installation

### Clone the repository

```bash
git clone https://github.com/think-elearn/toki-pona-ai
cd toki-pona-ai
```

### Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Set up the database

Create a PostgreSQL database named `toki_pona_db`.

```bash
psql -U postgres
CREATE DATABASE toki_pona_db;
\q
```

Then create a `.env` file with the following command:

```bash
echo "DATABASE_URL=postgres://postgres:postgres@localhost:5432/toki_pona_db
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
DEBUG=True" > .env
```

### Apply migrations

```bash
python manage.py migrate
```

### Create superuser

```bash
python manage.py createsuperuser
```

### Set up pre-commit hooks

Install pre-commit if you haven't already:

```bash
pip install pre-commit
```

Then set up the pre-commit hooks:

```bash
pre-commit install
```

### Run the development server

```bash
python manage.py runserver
```

## Seed the database with sample data

```bash
python manage.py load_sample_phrases
python manage.py load_sample_glyphs
python manage.py load_sample_signs
```

## Testing

```bash
pytest
```
