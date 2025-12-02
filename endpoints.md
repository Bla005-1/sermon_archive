# Frontend Endpoints
Notes on every endpoint the rendered UI or client-side JS calls, the request shape it expects, and how the response is used.

## Page routes
- `GET /` (`archive.views.sermon_list`): Loads the sermon list page. Optional query `q` filters by title (`?q=Advent`). Renders the full page HTML shown from the nav “Sermons” link.
- `GET /sermons/new` + `POST /sermons/new` (`archive.views.sermon_create`): Sermon creation form. POST expects form fields `preached_on`, `title` (required), `speaker_name`, `series_name`, `location_name`, `notes_md`. On success redirects to the new sermon detail; on error re-renders the form with the submitted values.
- `GET /sermons/<pk>` (`archive.views.sermon_detail`): Sermon detail page. Optional query params `from_ref` and `from_translation` are used to render a “Back to results” link to Verse Tools. Displays passages/attachments widgets that make follow-up HTMX calls below.
- `GET /sermons/<pk>/edit` + `POST /sermons/<pk>/edit` (`archive.views.sermon_edit`): Same fields as creation. POST persists updates and redirects to the detail page; validation errors re-render the form.
- `GET /verses/tools` + `POST /verses/tools` (`archive.views.widgets.verse_tools`): Verse Tools page. GET accepts `ref` (required to load results), optional `translation`; also accepts `verse_id`, `start_verse_id`, `end_verse_id` to resolve a ref from IDs. POST is used by the in-page form with hidden fields `reference`, `start_verse_id`, `end_verse_id`, `selected_translation`, and `csrfmiddlewaretoken`. Two actions:
  - `form_action=save`: Saves `note_md` for the selected verse (compares to `note_original`) and redirects back to the same ref on success.
  - `form_action=add_to_widget`: Uses the currently selected translation to build a BibleWidget entry; on success stays on the page and shows flash messaging.
  The GET/POST response is full-page HTML.
- `GET /verses/widget` + `POST /verses/widget` (`archive.views.widgets.bible_widget_list`): BibleWidget management page. GET renders the list. POST expects `entry_id` and `action` with optional `display_text`:
  - `action=update_text` with `display_text` updates text.
  - `action=weight_up|weight_down` adjusts weight.
  - `action=delete` removes the entry.
  Each POST redirects back to the same page to show messages.

## HTMX partial endpoints (fragments returned as HTML)
- `POST /sermons/<pk>/ui/passage/add` (`archive.views.passages.passage_add`): Called from the “Add passage” button. Expects `ref_text`, `context_note`, and CSRF token. Returns `archive/_partials/passage_list.html` to replace `#passage-list`. 400 if the ref cannot be parsed; 403 if the user lacks permission.
- `GET /sermons/<pk>/ui/passage/<ord>/edit` (`archive.views.passages.passage_edit`): Renders the same partial with the passage row in edit mode. Triggered by the “Edit” buttons. `?cancel=1` exits edit mode. Response replaces `#passage-list`.
- `POST /sermons/<pk>/ui/passage/<ord>/edit` (`archive.views.passages.passage_edit`): Saves a passage’s `context_note` field, then returns the updated passage list partial for `#passage-list`. 400 on save errors.
- `GET /sermons/<pk>/ui/passage/<ord>/delete` (`archive.views.passages.passage_delete`): Deletes a passage and re-renders the passage list partial. Triggered by “Delete” buttons with `hx-confirm`.
- `POST /sermons/<pk>/attachments` (`archive.views.attachments.attachment_upload`): Multipart upload from the Attachments form. Field `attachment` must contain the file; CSRF token required. Returns the `archive/_partials/attachment_list.html` fragment that replaces `#attachment-list`. 400 on validation errors.
- `GET /sermons/<pk>/attachments/<att_id>/delete` (`archive.views.attachments.attachment_delete`): Deletes an attachment and returns the updated attachment list partial.
- `GET /sermons/<pk>/attachments/<att_id>/download` (`archive.views.attachments.attachment_download`): Streams the file for download. Used by “Download” links in the attachment list (regular navigation, not HTMX).

## JSON APIs used by client-side JS
- `GET /api/verse` (`archive.api_verse.verse_lookup`): Used by `sermon_site/static/js/verse_tools.js` to load cross references and commentaries. Query params:
  - `ref` (required): Bible reference text (e.g., `John 3:16-18`).
  - `translation` (optional, defaults to `ESV` if available).
  Response is JSON shaped like:
  ```json
  {
    "query": {"ref": "John 3:16", "translation": "ESV"},
    "parsed_ref": "John 3:16",
    "verse_text": "For God so loved the world …",
    "count": 1,
    "results": [{
      "verse_id": 43003016,
      "book": "John",
      "chapter": 3,
      "verse": 16,
      "translation": "ESV",
      "text": "For God so loved the world…",
      "notes": [{"note_id": 1, "note_md": "*Draft*", "created_at": "...", "updated_at": "..."}],
      "cross_refs": [{"reference": "Romans 5:8", "to_start_id": 45005008, "to_end_id": 45005008, "preview_text": "But God shows his love…", "votes": 0, "note": ""}],
      "commentaries": [{"commentary_id": 10, "father_name": "Augustine", "display_name": "Augustine of Hippo", "text": "...", "start_verse_id": 43003016, "end_verse_id": 43003016, "reference": "John 3:16"}],
      "commentary_count": 1
    }]
  }
  ```
  Frontend usage:
  - Cross-reference panel builds a verse-id → `[{"reference", "preview_text"}]` map from `results[*].cross_refs`.
  - Commentary panel flattens `results[*].commentaries` into a list and renders `display_name|father_name`, `reference`, and `text`.
  404 is returned if `ref` cannot be parsed.

## Auth endpoints
- `GET /login/` + `POST /login/` (Django auth `LoginView` with template `sermon_site/templates/login.html`): Expects default Django auth form fields `username` and `password`. On success redirects to the next page or `/`.
- `POST /logout/` (Django auth `LogoutView`): The header uses `header_actions.js` to send a same-origin POST with `X-CSRFToken`; on failure it falls back to navigating to the same URL with GET. Either path clears the session and redirects to the login page.
