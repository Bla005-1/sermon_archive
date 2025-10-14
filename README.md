# Sermon Archive (Django)

A private, local-first Django app for storing sermons, passages, and attachments with fast manual entry and future-proof data design.

## Key Features
- **Sermon archive**: date, title, speaker, series, location, notes (Markdown).
- **Passages**: link each sermon to contiguous Scripture ranges.
- **Attachments**: upload slides, PDFs, images, audio; stored under a predictable media root.
- **Clean data model**: normalized tables with foreign keys; portable and extensible.
- **Simple UI**: list, create/edit, and detail views for sermons (templates under `sermon_site/templates/`).

## Tech Stack
- Python 3.12+, Django 5.x
- MySQL 8.0+ (InnoDB, utf8mb4)
- HTMX (optional) / vanilla HTML templates
- Nginx + Gunicorn (production suggestion)

---

## Quick Start (Development)

### 1) Clone & enter the project
```bash
git clone <your-repo-url> sermon-archive
cd sermon-archive
```

### 2) Python environment
```bash
# Using Poetry (recommended)
poetry install
poetry run python manage.py --version
# Or using venv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # if using pip
```

### 3) Configure environment
Create a `.env` from the example and fill in values:
```bash
cp .env.example .env
```
Common settings:
```
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1

# MySQL (preferred)
DB_NAME=sermon_archive
DB_USER=sermon_user
DB_PASSWORD=yourpass
DB_HOST=127.0.0.1
DB_PORT=3306

# Paths (override if needed)
MEDIA_ROOT=./sermon_site/media
STATIC_ROOT=./staticfiles
```

### 4) Database
Create the MySQL database and user, then run migrations:
```sql
CREATE DATABASE sermon_archive CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'sermon_user'@'%' IDENTIFIED BY 'yourpass';
GRANT ALL PRIVILEGES ON sermon_archive.* TO 'sermon_user'@'%';
FLUSH PRIVILEGES;
```
```bash
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
```

### 5) Run the dev server
```bash
poetry run python manage.py runserver
```
Visit http://127.0.0.1:8000/ and log in.

---


**Primary Django app**: `archive`  
**Project**: `sermon_site`

---

## Data Model (Overview)

Core tables (summarized):
- `sermons`: sermon metadata + `notes_md` (Markdown).
- `sermon_passages`: contiguous verse ranges used in a sermon (start/end verse_id + `ref_text`, `ord`).
- `attachments`: files linked to a sermon.
- Bible domain is normalized (`bible_books`, `bible_verses`, `verse_texts`, `verse_notes`).

> Tip: Standardize book names with Arabic numerals (e.g., `1 Samuel`, `2 Corinthians`).

### Migrations
```bash
poetry run python manage.py makemigrations
poetry run python manage.py migrate
```

---

## Static & Media

- **Static files** live in `sermon_site/static/` during development. In production, collect them to `STATIC_ROOT`:
  ```bash
  poetry run python manage.py collectstatic
  ```
- **Media files** (uploads) are stored under `MEDIA_ROOT` (default: `sermon_site/media/`). Make sure this directory exists and is writable.

**Templates**: Remember to load the static tag at the top of templates that use static assets:
```django
{% load static %}
<link rel="stylesheet" href="{% static 'css/app.css' %}">
```

---

## Useful Management Commands

```bash
# Create an initial staff superuser
poetry run python manage.py createsuperuser

# Dump/load data
poetry run python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > backup.json
poetry run python manage.py loaddata backup.json

# Check for template or model issues
poetry run python manage.py check
```

---

## Developer Tips

- Keep translations separate in `verse_texts`. Don’t create duplicate rows in `bible_verses` for new translations; only add `verse_texts` rows.
- Use `sermon_passages.ord` to control the display order of passages.
- Prefer `utf8mb4` at the DB and connection level.
- For import routines, build once-off scripts that join `(book_id, chapter, verse)` to map raw source data to your canonical IDs.
