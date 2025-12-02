# Sermon Archive API (Django + DRF)

A JSON-only backend for storing sermons, linked passages, and file attachments. The project now exposes REST endpoints under `/api/` and no longer ships any HTML templates or front-end assets.

## Project layout
See `project_tree.txt` for a concise map of the codebase. Django configuration now lives in `config/`, the API router is centralized under `api/urls.py`, and the sermons app resides in `apps/sermons/`. Front-end templates and static assets have been removed; only the API and supporting services remain.

## Development setup
1. **Install dependencies**
   ```bash
   poetry install
   # If Poetry reports that the lock file is outdated after adding Django REST Framework,
   # re-run `poetry lock` when you have internet access.
   ```
2. **Configure environment**
   ```bash
   cp .env.template .env
   # Set DB credentials, secret key, and storage paths as needed.
   ```
3. **Migrate and create a user**
   ```bash
   poetry run python manage.py migrate
   poetry run python manage.py createsuperuser
   ```
4. **Run the API server**
   ```bash
   poetry run python manage.py runserver
   ```
5. **Call the API**
   Use any HTTP client (curl, HTTPie, Postman) against `http://127.0.0.1:8000/api/` with authenticated requests. See `API_REFERENCE.md` for endpoint-level request and response details.

## Data model highlights
- **Sermons**: date preached, title, speaker, series, location, notes (Markdown), timestamps.
- **Passages**: ordered links to Bible verses with optional context notes.
- **Attachments**: file metadata and server-side storage paths.

Uploads are saved beneath `SERMON_STORAGE_ROOT` (configure in `.env`).
