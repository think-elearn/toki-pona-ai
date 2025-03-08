# AI-Powered Toki Pona Language Learning App

This is an AI-powered Toki Pona language learning app based on prototypes created during ExamPro's 2025 GenAI Essentials bootcamp. See the [bootcamp repository](https://github.com/dr-rompecabezas/free-genai-bootcamp-2025) for the related projects.

## Installation

### Install dependencies

```bash
pip install -r requirements.txt requirements-dev.txt
```

### Configure the database

For SQLite (for development):

```bash
echo "DATABASE_ENGINE=sqlite3
DATABASE_NAME=sqlite3
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
DEBUG=True" > .env
```

For PostgreSQL (default):

```bash
echo "DATABASE_ENGINE=postgresql
DATABASE_NAME=toki_pona_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=localhost
DATABASE_PORT=5432
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
