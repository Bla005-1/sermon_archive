# Backend tests

This folder contains automated pytest coverage and manual API testing assets.

- `test_*_api.py`: FastAPI tests using an isolated in-memory SQLite database.
- `factories.py`: Seed helpers for API test data.
- `rest_client/`: VS Code REST Client request files.

Run the automated suite from `backend/`:

```powershell
poetry run pytest
```

The pytest fixtures override the app database dependency, auth dependency for
protected route tests, and attachment storage root. They do not connect to the
production database.
