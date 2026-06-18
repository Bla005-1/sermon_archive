"""Backend-owned search intent resolution and unified search proxy."""

from __future__ import annotations

import re
from urllib.parse import quote_plus

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db.models import LibraryItems, LibraryItemUnits, Sermons
from app.services._reference import format_ref, parse_reference
from sermon_archive.schemas import (
    SearchHit,
    SearchReferenceResponse,
    SearchResultsResponse,
)


def search(
    db: Session,
    q: str,
    limit: int = 10,
    offset: int = 0,
    domains: list[str] | None = None,
) -> SearchReferenceResponse | SearchResultsResponse:
    """Resolve reference intent locally, otherwise proxy unified search."""
    query = (q or "").strip()
    if not query:
        raise HTTPException(
            status_code=400, detail="Provide a query in the 'q' query param."
        )

    try:
        start, end = parse_reference(db, query)
    except ValueError:
        return _proxy_or_fallback(
            db=db,
            query=query,
            limit=limit,
            offset=offset,
            domains=domains,
        )

    reference = format_ref(start, end)
    return SearchReferenceResponse(
        reference=reference,
        canonical_url=f"/verse?ref={quote_plus(reference)}",
    )


def _proxy_or_fallback(
    db: Session,
    query: str,
    limit: int,
    offset: int,
    domains: list[str] | None,
) -> SearchResultsResponse:
    try:
        return _proxy_unified_search(
            query=query,
            limit=limit,
            offset=offset,
            domains=domains,
        )
    except (httpx.HTTPError, ValueError, ValidationError):
        return _fallback_keyword_search(
            db=db,
            query=query,
            limit=limit,
            offset=offset,
            domains=domains,
        )


def _proxy_unified_search(
    query: str,
    limit: int,
    offset: int,
    domains: list[str] | None,
) -> SearchResultsResponse:
    base_url = f"http://{settings.sermon_search_host}:{settings.sermon_search_port}"
    params: list[tuple[str, str | int]] = [
        ("q", query),
        ("limit", limit),
        ("offset", offset),
    ]
    for domain in domains or []:
        params.append(("domains", domain))

    response = httpx.get(
        f"{base_url}/api/search",
        params=params,
        timeout=settings.sermon_search_timeout_seconds,
    )
    if response.status_code >= 400:
        raise ValueError("Sermon search returned an error response.")
    payload = response.json()

    return SearchResultsResponse(
        query=str(payload.get("query") or query),
        total=int(payload.get("total") or 0),
        results=[
            SearchHit.model_validate(result)
            for result in payload.get("results") or []
        ],
    )


def _fallback_keyword_search(
    db: Session,
    query: str,
    limit: int,
    offset: int,
    domains: list[str] | None,
) -> SearchResultsResponse:
    terms = _tokenize(query)
    if not terms:
        return SearchResultsResponse(query=query, total=0, results=[])

    allowed_domains = {domain.lower() for domain in domains or []}
    results: list[SearchHit] = []
    if not allowed_domains or "sermon" in allowed_domains:
        results.extend(_fallback_sermons(db=db, terms=terms))
    if not allowed_domains or "library" in allowed_domains:
        results.extend(_fallback_library_items(db=db, terms=terms))
        results.extend(_fallback_library_units(db=db, terms=terms))

    total = len(results)
    return SearchResultsResponse(
        query=query,
        total=total,
        results=results[offset : offset + limit],
    )


def _fallback_sermons(db: Session, terms: list[str]) -> list[SearchHit]:
    searchable = _combined_text(Sermons.title, Sermons.notes_markdown)
    rows = db.scalars(
        select(Sermons)
        .where(_all_terms_match(searchable, terms))
        .order_by(Sermons.preached_on.desc(), Sermons.sermon_id.desc())
    ).all()
    return [
        SearchHit(
            result_type="sermon",
            resource_id=str(row.sermon_id),
            title=row.title,
            subtitle=row.speaker_name,
            preview_text=_preview(row.notes_markdown or row.title),
            href=f"/sermons/{row.sermon_id}",
            score=float(len(terms)),
        )
        for row in rows
    ]


def _fallback_library_items(db: Session, terms: list[str]) -> list[SearchHit]:
    searchable = _combined_text(
        LibraryItems.title,
        LibraryItems.author_name,
        LibraryItems.description_text,
    )
    rows = db.scalars(
        select(LibraryItems)
        .where(_all_terms_match(searchable, terms))
        .order_by(LibraryItems.title, LibraryItems.library_item_id)
    ).all()
    return [
        SearchHit(
            result_type="library",
            resource_id=str(row.library_item_id),
            title=row.title,
            subtitle=row.author_name,
            preview_text=_preview(row.description_text or row.title),
            href=f"/library/items/{row.library_item_id}",
            score=float(len(terms)),
        )
        for row in rows
    ]


def _fallback_library_units(db: Session, terms: list[str]) -> list[SearchHit]:
    searchable = _combined_text(
        LibraryItems.title,
        LibraryItems.author_name,
        LibraryItems.description_text,
        LibraryItemUnits.unit_title,
        LibraryItemUnits.content_text,
        LibraryItemUnits.content_text_markdown,
    )
    rows = db.scalars(
        select(LibraryItemUnits)
        .join(
            LibraryItems,
            LibraryItems.library_item_id == LibraryItemUnits.library_item_id,
        )
        .options(joinedload(LibraryItemUnits.library_item))
        .where(_all_terms_match(searchable, terms))
        .order_by(
            LibraryItems.title,
            LibraryItemUnits.library_item_id,
            LibraryItemUnits.unit_order,
        )
    ).all()
    results: list[SearchHit] = []
    for row in rows:
        title = row.unit_title or row.library_item.title
        preview_text = row.content_text or row.content_text_markdown or title
        results.append(
            SearchHit(
                result_type="library",
                resource_id=f"{row.library_item_id}:unit:{row.library_item_unit_id}",
                title=title,
                subtitle=row.library_item.title,
                preview_text=_preview(preview_text),
                href=f"/library/items/{row.library_item_id}",
                score=float(len(terms)),
            )
        )
    return results


def _tokenize(query: str) -> list[str]:
    return re.findall(r"[\w']+", query.lower())


def _combined_text(*columns):
    parts = [func.coalesce(column, "") for column in columns]
    expression = parts[0]
    for part in parts[1:]:
        expression = expression + " " + part
    return func.lower(expression)


def _all_terms_match(searchable, terms: list[str]):
    return and_(*[searchable.ilike(f"%{term}%") for term in terms])


def _preview(value: str, max_length: int = 220) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 1].rstrip()}..."
