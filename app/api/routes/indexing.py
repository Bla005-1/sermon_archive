"""Staff-only proxy for search indexing operations and audit data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Sermons
from app.dependencies import get_db, require_staff
from app.services import index_sync_service, search_index_client
from sermon_archive.schemas import (
    IndexDocumentAudit,
    IndexDocumentList,
    IndexJobAudit,
    IndexJobList,
    IndexJobSubmission,
    IndexOverview,
    IndexRebuildSubmission,
    SermonCoverageItem,
)

router = APIRouter(tags=["indexing"], dependencies=[Depends(require_staff)])


@router.get("/overview", response_model=IndexOverview)
def index_overview(db: Session = Depends(get_db)) -> IndexOverview:
    sermons = db.scalars(select(Sermons).order_by(Sermons.sermon_id)).all()
    indexable = {
        str(sermon.sermon_id): sermon
        for sermon in sermons
        if (sermon.notes_markdown or "").strip()
    }
    try:
        payload = search_index_client.request("GET", "/api/index/overview")
        indexed = _indexed_sermons()
    except HTTPException as exc:
        return IndexOverview(
            search_available=False,
            source_sermon_count=len(sermons),
            non_indexable_sermon_count=len(sermons) - len(indexable),
            warnings=[f"Search index coverage unavailable: {exc.detail}"],
            outbox=index_sync_service.counts(db),
        )

    indexed_by_id = {item["source_id"]: item for item in indexed}
    missing_ids = set(indexable) - set(indexed_by_id)
    orphaned_ids = set(indexed_by_id) - {str(item.sermon_id) for item in sermons}
    stale_ids = {
        source_id
        for source_id, sermon in indexable.items()
        if source_id in indexed_by_id
        and _is_stale(sermon.updated_at, indexed_by_id[source_id].get("updated_at"))
    }

    payload.update(
        search_available=True,
        source_sermon_count=len(sermons),
        indexed_sermon_count=len(indexed),
        missing_sermon_count=len(missing_ids),
        stale_sermon_count=len(stale_ids),
        non_indexable_sermon_count=len(sermons) - len(indexable),
        orphaned_sermon_count=len(orphaned_ids),
        missing_sermons=[
            _source_coverage_item(indexable[source_id])
            for source_id in sorted(missing_ids, key=int)
        ],
        stale_sermons=[
            _source_coverage_item(
                indexable[source_id],
                indexed_at=indexed_by_id[source_id].get("indexed_at"),
            )
            for source_id in sorted(stale_ids, key=int)
        ],
        orphaned_sermons=[
            _orphaned_coverage_item(indexed_by_id[source_id])
            for source_id in sorted(orphaned_ids, key=int)
        ],
    )
    payload["outbox"] = index_sync_service.counts(db)
    return IndexOverview.model_validate(payload)


def _indexed_sermons() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    offset = 0
    limit = 200
    while True:
        page = search_index_client.request(
            "GET",
            "/api/index/documents",
            params={
                "domain": "sermon",
                "limit": limit,
                "offset": offset,
            },
        )
        page_items = page.get("items", [])
        items.extend(page_items)
        offset += len(page_items)
        if not page_items or offset >= int(page.get("total", 0)):
            return items


def _is_stale(source_updated_at, indexed_updated_at: Any) -> bool:
    if source_updated_at is None:
        return False
    if indexed_updated_at is None:
        return True
    indexed = (
        indexed_updated_at
        if isinstance(indexed_updated_at, datetime)
        else datetime.fromisoformat(str(indexed_updated_at).replace("Z", "+00:00"))
    )
    source = source_updated_at
    if source.tzinfo is None and indexed.tzinfo is not None:
        indexed = indexed.replace(tzinfo=None)
    elif source.tzinfo is not None and indexed.tzinfo is None:
        source = source.replace(tzinfo=None)
    return source > indexed


def _source_coverage_item(
    sermon: Sermons, *, indexed_at: Any = None
) -> SermonCoverageItem:
    return SermonCoverageItem(
        sermon_id=sermon.sermon_id,
        title=sermon.title,
        speaker_name=sermon.speaker_name,
        preached_on=sermon.preached_on,
        source_updated_at=sermon.updated_at,
        indexed_at=indexed_at,
    )


def _orphaned_coverage_item(document: dict[str, Any]) -> SermonCoverageItem:
    return SermonCoverageItem(
        sermon_id=int(document["source_id"]),
        title=str(document.get("title") or f"Sermon {document['source_id']}"),
        indexed_at=document.get("indexed_at"),
    )


@router.get("/documents", response_model=IndexDocumentList)
def index_documents(
    domain: str | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> IndexDocumentList:
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if domain is not None:
        params["domain"] = domain
    if q is not None:
        params["q"] = q
    return IndexDocumentList.model_validate(
        search_index_client.request("GET", "/api/index/documents", params=params)
    )


@router.get("/documents/{domain}/{source_id}", response_model=IndexDocumentAudit)
def index_document(domain: str, source_id: str) -> IndexDocumentAudit:
    return IndexDocumentAudit.model_validate(
        search_index_client.request("GET", f"/api/index/documents/{domain}/{source_id}")
    )


@router.get("/jobs", response_model=IndexJobList)
def index_jobs(
    status: str | None = None,
    job_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> IndexJobList:
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if status is not None:
        params["status"] = status
    if job_type is not None:
        params["job_type"] = job_type
    return IndexJobList.model_validate(
        search_index_client.request("GET", "/api/index/jobs", params=params)
    )


@router.get("/jobs/{job_id}", response_model=IndexJobAudit)
def index_job(job_id: int) -> IndexJobAudit:
    return IndexJobAudit.model_validate(
        search_index_client.request("GET", f"/api/index/jobs/{job_id}")
    )


@router.post("/sermons/{sermon_id}", status_code=202, response_model=IndexJobSubmission)
def index_sermon(sermon_id: int) -> IndexJobSubmission:
    return IndexJobSubmission.model_validate(search_index_client.queue_sermon(sermon_id))


@router.post("/rebuild", status_code=202, response_model=IndexRebuildSubmission)
def rebuild_index() -> IndexRebuildSubmission:
    return IndexRebuildSubmission.model_validate(search_index_client.rebuild())
