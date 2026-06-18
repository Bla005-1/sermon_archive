"""Schemas for the backend-owned search endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from sermon_archive.schemas.base import APIModel


class SearchHit(APIModel):
    result_type: str
    resource_id: str
    title: str
    subtitle: str | None = None
    preview_text: str
    href: str
    score: float


class SearchReferenceResponse(APIModel):
    intent: Literal["reference"] = "reference"
    reference: str
    canonical_url: str


class SearchResultsResponse(APIModel):
    intent: Literal["search"] = "search"
    query: str
    total: int = Field(ge=0)
    results: list[SearchHit] = Field(default_factory=list)


SearchResponse = SearchReferenceResponse | SearchResultsResponse
