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

## Naming Conventions

Database, ORM, and API schema fields use explicit snake_case names that describe the domain object:

- Table primary keys are table-specific, such as `sermon_id`, `sermon_passage_id`, `footnote_id`, and `widget_passage_id`.
- Foreign keys include the target role when a table points to the same target more than once, such as `source_verse_id`, `target_start_verse_id`, and `target_end_verse_id`.
- Bible location fields use `chapter_number` and `verse_number`.
- Reference display strings use `reference_text`; markdown content uses `*_markdown`.
- Avoid abbreviations in persistent/API names: use `display_order`, `relative_path`, `commentary_text`, and `vote_count` instead of short forms.
- SQL indexes and constraints use `idx_*`, `uq_*`, and `fk_*` prefixes followed by the table and role.

Route query parameters may stay concise where they are user-facing (`q`, `ref`, `chapter`), but request and response bodies should follow the schema names above.


## Environment Variables

Base values live in `.env.template`. Most important settings:

- `DATABASE_URL`: full SQLAlchemy DSN (required)
- `SERMON_STORAGE_ROOT`: root folder for attachment uploads
- `DEBUG`, `LOG_LEVEL`: runtime debugging/log level
- `SESSION_TTL_MINUTES`: session lifetime
- `TOKEN_TTL_MINUTES`: bearer token lifetime
- `CORS_ALLOWED_ORIGINS`: comma-separated CORS allowlist
- `CORS_ALLOW_CREDENTIALS`: allow credentials for CORS
- `ALLOWED_HOSTS`: comma-separated trusted hosts
- `COOKIE_SECURE`, `COOKIE_SAMESITE`: cookie behavior
- `SESSION_COOKIE_NAME`, `CSRF_COOKIE_NAME`: cookie names

For a browser client on a different domain, set:
- `COOKIE_SAMESITE=none`
- `COOKIE_SECURE=true`

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
- `GET /api/sermons/suggestions`
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
- `GET /api/sermons/{sermon_id}/passages/{sermon_passage_id}`
- `PUT /api/sermons/{sermon_id}/passages/{sermon_passage_id}`
- `PATCH /api/sermons/{sermon_id}/passages/{sermon_passage_id}`
- `DELETE /api/sermons/{sermon_id}/passages/{sermon_passage_id}`

`GET /api/sermons/suggestions` returns collection-level autocomplete values derived from existing sermons:

- `speakers`
- `series`
- `locations`

### Attachments (protected)

- `GET /api/attachments/{attachment_id}`
- `PUT /api/attachments/{attachment_id}`
- `PATCH /api/attachments/{attachment_id}`
- `DELETE /api/attachments/{attachment_id}`

### Verses

Public:
- `GET /api/verses`
- `GET /api/verses/search`
- `GET /api/verses/translations`

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

`GET /api/verses/translations` returns the distinct translation codes available for verse lookup and text search filters.

### Widget

Public:
- `GET /api/widget`
- `GET /api/widget/{widget_passage_id}`

Protected:
- `POST /api/widget`
- `PUT /api/widget/{widget_passage_id}`
- `PATCH /api/widget/{widget_passage_id}`
- `DELETE /api/widget/{widget_passage_id}`

## Manual Testing

Use the VS Code REST Client files in `tests/rest_client/`:

- `tests/rest_client/auth.rest`
- `tests/rest_client/protected_endpoints.rest`

Set credentials in your environment (`API_USERNAME`, `API_PASSWORD`) before running requests.

## Marked Bible Text
- If a word contains a `*`, then all following characters indicate features of that word.
  - `p` - Start a new paragraph.
  - `l` - Start a new line.
  - `n` - Start a new indented line.
  - `d` - Start a new doubly-indented line.
  - `c` - Start a new centered line.
  - `g` - Start a new right-aligned line.
  - `e` - Start a new left-aligned line.
  - `s` - Render with smallcaps.
  - `i` - Render with italics.
  - `b` - Render with bold.
  - `r` - Render as a redletter word of Christ.
- For example, a verse text might be: `For*pn the Lord*s watches over the way of the righteous, but*ln the way of the wicked leads to ruin.`
  - The first word (`For`) should start a new paragraph and be indented.
  - The third word (`Lord`) should be rendered with smallcaps.
  - The eleventh word (`but`) should start a new line and be indented.

## Bible Footnotes
- If a word contains a `*`, then all following characters indicate features of that word.
  - `r` - Indicates that the word is a cross-reference.
  - `i` - Render with italics.
- For example, a footnote text might be `2:2*r Or anointed one`.
  - The first word is a cross-reference that can be linked be `2:2` within the current book.
  
