# Sermon Archive API

FastAPI backend for sermon records, Bible reference lookup/search, commentary and cross-reference retrieval, verse notes, and widget passage management.

## Stack

- Python 3.11
- FastAPI
- SQLAlchemy 2.x
- MySQL (`mysql+pymysql`)
- Poetry

## What This API Provides

- Auth with either:
  - Session cookie (`/api/auth/login`, `/api/auth/me`, `/api/auth/refresh`, `/api/auth/logout`)
  - Bearer token (`/api/auth/token`, `/api/auth/token/revoke`)
- Sermons CRUD with nested passages and attachments
- Bible reference parsing + verse text lookup
- Free-text verse search with paging/filters
- Commentary and cross-reference lookup for references
- Verse notes CRUD
- Widget verse entries CRUD

## Project Layout

- `main.py`: FastAPI app entrypoint
- `app/config.py`: environment-backed settings
- `app/api/routes/`: API routes
- `app/services/`: domain/service logic
- `app/db/models.py`: SQLAlchemy models (database-first)
- `tests/rest_client/`: manual API requests for VS Code REST Client

## Prerequisites

1. Python 3.11+
2. Poetry
3. MySQL database with the expected schema/tables already present

Notes:
- This codebase is database-first and uses existing tables from `app/db/models.py`.
- There are no migrations in this repository.


## Environment Variables

Base values live in `.env.template`. Most important settings:

- `DATABASE_URL`: full SQLAlchemy DSN override
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: used if `DATABASE_URL` is not set
- `SERMON_STORAGE_ROOT`: root folder for attachment uploads
- `APP_DEBUG`, `APP_LOG_LEVEL`: runtime debugging/log level
- `APP_SESSION_TTL_MINUTES`: session lifetime
- `APP_TOKEN_TTL_MINUTES`: bearer token lifetime
- `APP_CORS_ALLOWED_ORIGINS`: comma-separated CORS allowlist
- `APP_COOKIE_SECURE`, `APP_COOKIE_SAMESITE`: cookie behavior

For a browser client on a different domain, set:
- `APP_COOKIE_SAMESITE=none`
- `APP_COOKIE_SECURE=true`

Attachment files are written under:

- `<SERMON_STORAGE_ROOT>/<year>/<sermon_id>/<generated_filename>`

## Authentication

Protected endpoints use:
1. `Authorization: Bearer <token>` first
2. Session cookie fallback (`sessionid` by default)

Common auth flow:

1. `POST /api/auth/token` with username/password
2. Use returned token as bearer auth
3. Call protected routes
4. `POST /api/auth/token/revoke` when done

Session-cookie flow is also available through `/api/auth/login`, `/api/auth/me`, `/api/auth/refresh`, `/api/auth/logout`.

Password verification supports only scrypt-formatted hashes (`scrypt$<salt>$<digest>`). Legacy plaintext fallbacks are not accepted.

For session-cookie auth, CSRF validation is required on state-changing methods (`POST`, `PUT`, `PATCH`, `DELETE`) via `X-CSRF-Token`.

## API Route Summary

### Auth

- `GET /api/auth/csrf`
- `POST /api/auth/login`
- `POST /api/auth/token`
- `POST /api/auth/token/revoke`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/auth/refresh`

### Sermons (protected)

- `GET /api/sermons`
- `POST /api/sermons`
- `GET /api/sermons/{sermon_id}`
- `PUT /api/sermons/{sermon_id}`
- `PATCH /api/sermons/{sermon_id}`
- `DELETE /api/sermons/{sermon_id}`
- `GET /api/sermons/{sermon_id}/attachments`
- `POST /api/sermons/{sermon_id}/attachments` (multipart file upload)
- `GET /api/sermons/{sermon_id}/attachments/{attachment_id}/download` (file download)
- `GET /api/sermons/{sermon_id}/passages`
- `POST /api/sermons/{sermon_id}/passages`
- `GET /api/sermons/{sermon_id}/passages/{id}`
- `PUT /api/sermons/{sermon_id}/passages/{id}`
- `PATCH /api/sermons/{sermon_id}/passages/{id}`
- `DELETE /api/sermons/{sermon_id}/passages/{id}`
- `GET /api/sermons/suggestions`

### Attachments (protected)

- `GET /api/attachments/{id}`
- `PUT /api/attachments/{id}`
- `PATCH /api/attachments/{id}`
- `DELETE /api/attachments/{id}`

### Verses

Public:
- `GET /api/verses`
- `GET /api/verses/search`

Protected:
- `GET /api/verses/commentaries`
- `GET /api/verses/crossrefs`
- `GET /api/verses/notes`
- `POST /api/verses/notes`
- `GET /api/verses/notes/{note_id}`
- `PUT /api/verses/notes/{note_id}`
- `PATCH /api/verses/notes/{note_id}`
- `DELETE /api/verses/notes/{note_id}`
- `GET /api/verses/sermons`

### Widget

Public:
- `GET /api/widget`
- `GET /api/widget/{id}`

Protected:
- `POST /api/widget`
- `PUT /api/widget/{id}`
- `PATCH /api/widget/{id}`
- `DELETE /api/widget/{id}`

## Manual Testing

Use the VS Code REST Client files in `tests/rest_client/`:

- `tests/rest_client/auth.rest`
- `tests/rest_client/protected_endpoints.rest`

Set credentials in your environment (`API_USERNAME`, `API_PASSWORD`) before running requests.
