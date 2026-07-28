"""Schemas for staff index synchronization and audit endpoints."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import Field

from sermon_archive.schemas.base import APIModel


class IndexJobAudit(APIModel):
    job_id: int
    job_type: Literal["source", "rebuild"]
    status: str
    stage: str
    index_method: str
    generation_id: str | None = None
    total_items: int = 0
    completed_items: int = 0
    current_domain: str | None = None
    current_source_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None = None
    started_at: dt.datetime
    updated_at: dt.datetime
    completed_at: dt.datetime | None = None


class IndexJobSubmission(APIModel):
    job_id: int
    sermon_id: int
    status: str
    stage: str
    status_url: str
    message: str | None = None


class IndexRebuildSubmission(APIModel):
    job_id: int
    status: str
    status_url: str


class IndexJobList(APIModel):
    total: int
    limit: int
    offset: int
    items: list[IndexJobAudit]


class IndexDocumentSummary(APIModel):
    domain: str
    source_id: str
    title: str
    subtitle: str | None = None
    href: str
    indexed_at: dt.datetime
    updated_at: dt.datetime | None = None
    unit_count: int
    preprocessing_version: str
    llm_model: str | None = None
    prompt_version: str | None = None
    embedding_model: str | None = None
    embedding_version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexDocumentList(APIModel):
    total: int
    limit: int
    offset: int
    items: list[IndexDocumentSummary]


class IndexUnitAudit(APIModel):
    unit_id: str
    unit_order: int
    unit_type: str
    title: str
    content_text: str
    summary: str
    topics: list[str]
    href: str | None = None


class IndexDocumentAudit(IndexDocumentSummary):
    units: list[IndexUnitAudit]


class SermonCoverageItem(APIModel):
    sermon_id: int
    title: str
    speaker_name: str | None = None
    preached_on: dt.date | None = None
    source_updated_at: dt.datetime | None = None
    indexed_at: dt.datetime | None = None


class IndexOverview(APIModel):
    search_available: bool = True
    active_generation: dict[str, Any] | None = None
    domains: list[dict[str, Any]] = Field(default_factory=list)
    source_sermon_count: int | None = None
    indexed_sermon_count: int = 0
    missing_sermon_count: int | None = None
    stale_sermon_count: int | None = None
    non_indexable_sermon_count: int = 0
    orphaned_sermon_count: int | None = None
    missing_sermons: list[SermonCoverageItem] = Field(default_factory=list)
    stale_sermons: list[SermonCoverageItem] = Field(default_factory=list)
    orphaned_sermons: list[SermonCoverageItem] = Field(default_factory=list)
    recent_job_counts: dict[str, int] = Field(default_factory=dict)
    latest_failures: list[IndexJobAudit] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    outbox: dict[str, int] = Field(default_factory=dict)
