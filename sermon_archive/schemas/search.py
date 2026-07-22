"""Schemas for the backend-owned search endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from sermon_archive.schemas.base import APIModel


class SearchMatch(APIModel):
    resource_id: str
    title: str
    subtitle: str | None = None
    preview_text: str
    href: str
    score: float


class SearchResultGroup(APIModel):
    result_type: str
    group_level: Literal["sermon", "library_section", "commentary", "verse"]
    group_id: str
    title: str
    source_id: str
    source_title: str
    source_subtitle: str | None = None
    href: str
    score: float
    match_count: int = Field(ge=1)
    matches: list[SearchMatch] = Field(min_length=1)


class SearchReferenceResponse(APIModel):
    intent: Literal["reference"] = "reference"
    reference: str
    canonical_url: str


class SearchResultsResponse(APIModel):
    intent: Literal["search"] = "search"
    query: str
    total: int = Field(ge=0)
    results: list[SearchResultGroup] = Field(default_factory=list)


SearchResponse = SearchReferenceResponse | SearchResultsResponse
