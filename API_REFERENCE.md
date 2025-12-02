# API reference

Base path: `/api/`. All endpoints use JSON request/response bodies unless otherwise noted. Session-based authentication is provided by the auth endpoints below; include the CSRF token for mutating requests.

## Authentication
- `POST /api/auth/login/`: Body `{"username": "...", "password": "..."}`. Returns the authenticated user object and sets the session cookie.
- `POST /api/auth/logout/`: Clears the authenticated session. Returns 204 on success.
- `GET /api/auth/refresh/`: Returns the current user object if the session cookie is still valid.
- `GET /api/auth/me/`: Returns the current user object, useful for introspection once authenticated.

User payload shape:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "first_name": "Admin",
  "last_name": "User",
  "is_active": true,
  "is_staff": true
}
```

## Sermons
- `GET /api/sermons/`: Lists sermons ordered by `preached_on` and `sermon_id` descending. Optional query `q` filters by title substring. Each item embeds `passages` and `attachments`.
- `POST /api/sermons/`: Creates a sermon. Body fields: `preached_on` (YYYY-MM-DD), `title` (required), `speaker_name`, `series_name`, `location_name`, `notes_md`.
- `GET /api/sermons/{sermon_id}/`: Retrieves a sermon with embedded passages and attachments.
- `PUT/PATCH /api/sermons/{sermon_id}/`: Updates sermon fields.
- `DELETE /api/sermons/{sermon_id}/`: Removes a sermon.

Sermon payload shape:
```json
{
  "sermon_id": 42,
  "preached_on": "2024-01-07",
  "title": "Hope Renewed",
  "speaker_name": "Rev. Smith",
  "series_name": "New Beginnings",
  "location_name": "Main Campus",
  "notes_md": "# Outline...",
  "created_at": "2024-01-05T12:00:00Z",
  "updated_at": "2024-01-06T15:30:00Z",
  "passages": [
    {
      "id": 7,
      "sermon": 42,
      "start_verse": {"verse_id": 43003016, "book": {"book_id": 43, "name": "John", "order_num": 43, "testament": "NT"}, "chapter": 3, "verse": 16},
      "end_verse": null,
      "ref_text": "John 3:16",
      "context_note": "Opening reading",
      "ord": 1
    }
  ],
  "attachments": [
    {
      "attachment_id": 3,
      "sermon": 42,
      "rel_path": "sermons/42/notes.pdf",
      "original_filename": "notes.pdf",
      "mime_type": "application/pdf",
      "byte_size": 12345,
      "created_at": "2024-01-06T15:00:00Z"
    }
  ]
}
```

### Sermon passages
- `GET /api/sermons/{sermon_id}/passages/`: Lists ordered passages for a sermon.
- `POST /api/sermons/{sermon_id}/passages/`: Adds a passage to a sermon. Body fields: `start_verse_id` (required), `end_verse_id` (optional), `ref_text` (optional string), `context_note` (optional string). Passages are auto-ordered.
- `GET /api/sermons/{sermon_id}/passages/{id}/`: Retrieves a passage.
- `PUT/PATCH /api/sermons/{sermon_id}/passages/{id}/`: Updates `start_verse_id`, `end_verse_id`, `ref_text`, or `context_note`.
- `DELETE /api/sermons/{sermon_id}/passages/{id}/`: Deletes the passage and reorders remaining entries.
- `GET/PUT/PATCH/DELETE /api/sermons/passages/{id}/`: Global passage detail without the sermon prefix (same payload fields).

Passage payload shape (nested serializer output):
```json
{
  "id": 7,
  "sermon": 42,
  "start_verse": {"verse_id": 43003016, "book": {"book_id": 43, "name": "John", "order_num": 43, "testament": "NT"}, "chapter": 3, "verse": 16},
  "end_verse": {"verse_id": 43003017, "book": {"book_id": 43, "name": "John", "order_num": 43, "testament": "NT"}, "chapter": 3, "verse": 17},
  "ref_text": "John 3:16-17",
  "context_note": "Gospel focus",
  "ord": 2
}
```

### Sermon attachments
- `GET /api/sermons/{sermon_id}/attachments/`: Lists attachments for a sermon ordered newest first.
- `POST /api/sermons/{sermon_id}/attachments/`: Uploads a file. Multipart/form-data with `file` required. Returns attachment metadata.
- `GET /api/sermons/{sermon_id}/attachments/{attachment_id}/`: Retrieves a single attachment record.
- `DELETE /api/sermons/{sermon_id}/attachments/{attachment_id}/`: Deletes the attachment and removes the stored file.
- `GET /api/sermons/{sermon_id}/attachments/{attachment_id}/download/`: Streams the file download.
- `GET/PUT/PATCH/DELETE /api/attachments/{attachment_id}/`: Global attachment detail by ID.
- `GET /api/attachments/{attachment_id}/download/`: Global attachment download.

Attachment payload shape:
```json
{
  "attachment_id": 3,
  "sermon": 42,
  "rel_path": "sermons/42/notes.pdf",
  "original_filename": "notes.pdf",
  "mime_type": "application/pdf",
  "byte_size": 12345,
  "created_at": "2024-01-06T15:00:00Z"
}
```

## Bible tools
- `GET /api/bible/lookup/?q=John+3:16-18`: Parses a Bible reference. Returns `start`, `end`, and formatted `reference` using verse IDs and book metadata.
- `GET /api/bible/notes/`: Lists verse notes ordered by `updated_at` descending. Optional query `verse_id` filters notes for a specific verse.
- `POST /api/bible/notes/`: Creates a verse note. Body fields: `verse_id` (required) and `note_md` (Markdown).
- `GET/PUT/PATCH/DELETE /api/bible/notes/{note_id}/`: Retrieves, updates, or deletes a verse note.

Verse note payload shape:
```json
{
  "note_id": 12,
  "verse": {"verse_id": 43003016, "book": {"book_id": 43, "name": "John", "order_num": 43, "testament": "NT"}, "chapter": 3, "verse": 16},
  "note_md": "*Draft note*",
  "created_at": "2024-01-06T15:00:00Z",
  "updated_at": "2024-01-06T15:10:00Z"
}
```

## Search
- `GET /api/search/?q=hope`: Returns up to 10 sermons with titles containing the query.
- `GET /api/search/ref/?q=John+3:16-17`: Parses a Bible reference and returns `reference`, `start`, and `end` verse metadata.

Search response shape:
```json
{
  "sermons": [
    {
      "sermon_id": 42,
      "preached_on": "2024-01-07",
      "title": "Hope Renewed",
      "speaker_name": "Rev. Smith",
      "series_name": "New Beginnings",
      "location_name": "Main Campus",
      "notes_md": "# Outline...",
      "created_at": "2024-01-05T12:00:00Z",
      "updated_at": "2024-01-06T15:30:00Z",
      "passages": [],
      "attachments": []
    }
  ]
}
```

## Bible widget
- `GET /api/widget/`: Lists Bible widget verses.
- `POST /api/widget/`: Creates a widget entry. Body fields: `start_verse_id` (required), `end_verse_id` (required), `translation`, `ref`, `display_text` (optional), `weight` (default ordering weight).
- `GET /api/widget/{id}/`: Retrieves a widget entry.
- `PUT/PATCH /api/widget/{id}/`: Updates widget fields.
- `DELETE /api/widget/{id}/`: Deletes a widget entry.

Bible widget payload shape:
```json
{
  "id": 5,
  "start_verse": {"verse_id": 43003016, "book": {"book_id": 43, "name": "John", "order_num": 43, "testament": "NT"}, "chapter": 3, "verse": 16},
  "end_verse": {"verse_id": 43003018, "book": {"book_id": 43, "name": "John", "order_num": 43, "testament": "NT"}, "chapter": 3, "verse": 18},
  "translation": "ESV",
  "ref": "John 3:16-18",
  "display_text": "For God so loved the world...",
  "weight": 1,
  "created_at": "2024-01-06T15:00:00Z",
  "updated_at": "2024-01-06T15:00:00Z"
}
```
