"""Staff-only proxy for search indexing operations and audit data."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

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
)

router = APIRouter(tags=["indexing"], dependencies=[Depends(require_staff)])


@router.get("/overview", response_model=IndexOverview)
def index_overview(db: Session = Depends(get_db)) -> IndexOverview:
    payload = search_index_client.request("GET", "/api/index/overview")
    payload["outbox"] = index_sync_service.counts(db)
    return IndexOverview.model_validate(payload)


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
