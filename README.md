# AI-Powered Toki Pona Language Learning App

This is an AI-powered Toki Pona language learning app based on prototypes created during ExamPro's 2025 GenAI Essentials bootcamp. See the [bootcamp repository](https://github.com/dr-rompecabezas/free-genai-bootcamp-2025) for the related projects.

## Pre-requisites

- Python 3.9 or higher
- PostgreSQL

## Installation

### Install dependencies

```bash
pip install -r requirements.txt requirements-dev.txt
```

### Configure the application

Create a PostgreSQL database named `toki_pona_db`.

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
