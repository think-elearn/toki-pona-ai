# AI-Powered Toki Pona Language Learning App

[![Build Status](https://github.com/think-elearn/toki-pona-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/think-elearn/toki-pona-ai/actions)

This is an AI-powered Toki Pona language learning app based on prototypes created during ExamPro's 2025 GenAI Essentials bootcamp. See the original [bootcamp repository](https://github.com/dr-rompecabezas/free-genai-bootcamp-2025) for the projects that inspired this app.

## Pre-requisites

- Python 3.12
- PostgreSQL

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
