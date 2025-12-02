# Sermon Archive API (Django + DRF)

A JSON-only backend for storing sermons, linked passages, and file attachments. The project now exposes REST endpoints under `/api/` and no longer ships any HTML templates or front-end assets.

## API surface
- `GET /api/sermons/` — list sermons (filter with `?q=` on title).
- `POST /api/sermons/` — create a sermon.
- `GET /api/sermons/<sermon_id>/` — retrieve a sermon with nested passages and attachments.
- `PUT/PATCH /api/sermons/<sermon_id>/` — update sermon metadata.
- `DELETE /api/sermons/<sermon_id>/` — remove a sermon.
- `GET /api/sermons/<sermon_id>/passages/` — list passages for a sermon.
- `POST /api/sermons/<sermon_id>/passages/` — add a passage (provide `start_verse_id`, optional `end_verse_id`, `ref_text`, `context_note`).
- `GET/PATCH/DELETE /api/sermons/<sermon_id>/passages/<id>/` — manage a single passage.
- `GET /api/sermons/<sermon_id>/attachments/` — list attachments.
- `POST /api/sermons/<sermon_id>/attachments/` — upload a file using multipart form data with the `file` field.
- `DELETE /api/sermons/<sermon_id>/attachments/<id>/` — delete an attachment.
- `GET /api/sermons/<sermon_id>/attachments/<id>/download/` — download an attachment.

All endpoints require authentication (session or basic auth). Use the Django admin (`/admin/`) to create users or manage data directly.

## Project layout
See `project_tree.txt` for a concise map of the codebase. Front-end templates and static assets have been removed; only the API and supporting services remain.

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
   Use any HTTP client (curl, HTTPie, Postman) against `http://127.0.0.1:8000/api/` with authenticated requests.

## Data model highlights
- **Sermons**: date preached, title, speaker, series, location, notes (Markdown), timestamps.
- **Passages**: ordered links to Bible verses with optional context notes.
- **Attachments**: file metadata and server-side storage paths.

Uploads are saved beneath `SERMON_STORAGE_ROOT` (configure in `.env`).
