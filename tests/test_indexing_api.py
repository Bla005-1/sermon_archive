from __future__ import annotations

import datetime as dt

from fastapi import HTTPException

from app.api.routes import indexing
from app.services import sermons_service
from sermon_archive.schemas import Sermon
from tests.factories import seed_user


def _document(
    sermon_id: int,
    *,
    title: str,
    updated_at: dt.datetime,
    indexed_at: dt.datetime,
) -> dict:
    return {
        "domain": "sermon",
        "source_id": str(sermon_id),
        "title": title,
        "href": f"/sermon/{sermon_id}",
        "indexed_at": indexed_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "unit_count": 1,
        "preprocessing_version": "test",
        "metadata": {},
    }


def test_overview_reconciles_missing_stale_non_indexable_and_orphaned(
    db_session, monkeypatch
):
    owner = seed_user(db_session)
    missing = sermons_service.create_sermon(
        db_session,
        Sermon(title="Missing", notes_markdown="Searchable notes"),
        owner,
    )
    stale = sermons_service.create_sermon(
        db_session,
        Sermon(title="Stale", notes_markdown="Changed notes"),
        owner,
    )
    sermons_service.create_sermon(
        db_session,
        Sermon(title="Intentionally empty", notes_markdown="  "),
        owner,
    )
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    old = now - dt.timedelta(days=1)
    stale_row = db_session.get(indexing.Sermons, stale.sermon_id)
    stale_row.updated_at = now
    db_session.commit()

    documents = [
        _document(
            stale.sermon_id,
            title="Old stale title",
            updated_at=old,
            indexed_at=old,
        ),
        _document(999, title="Orphan", updated_at=old, indexed_at=old),
    ]

    def fake_request(_method, path, *, params=None, **_kwargs):
        if path == "/api/index/overview":
            return {"indexed_sermon_count": 2, "warnings": []}
        assert path == "/api/index/documents"
        offset = int(params["offset"])
        limit = int(params["limit"])
        return {
            "total": len(documents),
            "limit": limit,
            "offset": offset,
            "items": documents[offset : offset + limit],
        }

    monkeypatch.setattr(indexing.search_index_client, "request", fake_request)

    overview = indexing.index_overview(db_session)

    assert overview.search_available is True
    assert overview.source_sermon_count == 3
    assert overview.indexed_sermon_count == 2
    assert overview.missing_sermon_count == 1
    assert overview.missing_sermons[0].sermon_id == missing.sermon_id
    assert overview.stale_sermon_count == 1
    assert overview.stale_sermons[0].sermon_id == stale.sermon_id
    assert overview.non_indexable_sermon_count == 1
    assert overview.orphaned_sermon_count == 1
    assert overview.orphaned_sermons[0].sermon_id == 999


def test_overview_returns_local_health_when_search_is_unavailable(
    db_session, monkeypatch
):
    owner = seed_user(db_session)
    sermons_service.create_sermon(
        db_session,
        Sermon(title="Still canonical", notes_markdown="Searchable notes"),
        owner,
    )

    def unavailable(*_args, **_kwargs):
        raise HTTPException(status_code=503, detail="Sermon search is unavailable")

    monkeypatch.setattr(indexing.search_index_client, "request", unavailable)

    overview = indexing.index_overview(db_session)

    assert overview.search_available is False
    assert overview.source_sermon_count == 1
    assert overview.missing_sermon_count is None
    assert overview.stale_sermon_count is None
    assert overview.orphaned_sermon_count is None
    assert "unavailable" in overview.warnings[0]
    assert overview.outbox["pending"] == 1
