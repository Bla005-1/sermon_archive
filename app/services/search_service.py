"""Backend-owned search intent resolution and unified search proxy."""

from __future__ import annotations

import re
from urllib.parse import quote_plus, unquote

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.services import search_index_client
from app.services._reference import format_ref, parse_reference
from sermon_archive.schemas import (
    SearchReferenceResponse,
    SearchResultGroup,
    SearchResultsResponse,
)


UNAVAILABLE_MESSAGE = "Search is temporarily unavailable. Please try again."
INVALID_RESPONSE_MESSAGE = "Search returned an invalid response. Please try again."


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
        return _proxy_unified_search(
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


def _proxy_unified_search(
    query: str,
    limit: int,
    offset: int,
    domains: list[str] | None,
) -> SearchResultsResponse:
    request_payload: dict[str, object] = {
        "query": query,
        "match_mode": "auto",
        "limit": limit,
        "offset": offset,
    }
    if domains:
        request_payload["filters"] = {"domains": domains}

    try:
        payload = search_index_client.request(
            "POST", "/api/search/query", json=request_payload
        )
    except HTTPException as exc:
        if exc.status_code == 503:
            raise HTTPException(status_code=503, detail=UNAVAILABLE_MESSAGE) from exc
        raise HTTPException(status_code=502, detail=INVALID_RESPONSE_MESSAGE) from exc

    try:
        response = SearchResultsResponse.model_validate(
            {
                "query": payload.get("query") or query,
                "total": payload.get("total", 0),
                "results": payload.get("results", []),
            }
        )
    except (AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise HTTPException(status_code=502, detail=INVALID_RESPONSE_MESSAGE) from exc

    return response.model_copy(
        update={"results": [_with_frontend_hrefs(group) for group in response.results]}
    )


def _with_frontend_hrefs(group: SearchResultGroup) -> SearchResultGroup:
    matches = [
        match.model_copy(
            update={
                "href": _frontend_href(
                    group.result_type, match.resource_id, match.href
                )
            }
        )
        for match in group.matches
    ]
    return group.model_copy(
        update={
            "href": matches[0].href,
            "matches": matches,
        }
    )


def _frontend_href(result_type: str, resource_id: str, href: str) -> str:
    result_type = result_type.lower()
    if result_type == "sermon":
        sermon_id = _first_number(resource_id) or _path_id(href, "sermons")
        if sermon_id is not None:
            return _sermon_href(sermon_id)
    if result_type == "library":
        library_item_id = (
            _first_number(resource_id)
            or _path_id(href, "library/items")
            or _path_id(href, "library")
        )
        if library_item_id is not None:
            unit_id = _unit_number(resource_id)
            fragment = f"#library-unit-{unit_id}" if unit_id is not None else ""
            return f"{_library_item_href(library_item_id)}{fragment}"
    if result_type == "verse" and href.startswith("/verse/"):
        reference = unquote(href.removeprefix("/verse/"))
        if reference:
            return f"/verse?ref={quote_plus(reference)}"
    return href


def _first_number(value: str) -> int | None:
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def _unit_number(value: str) -> int | None:
    match = re.search(r":unit:(\d+)(?:$|:)", value)
    return int(match.group(1)) if match else None


def _path_id(href: str, prefix: str) -> int | None:
    match = re.match(rf"^/{re.escape(prefix)}/(\d+)(?:/|$)", href)
    return int(match.group(1)) if match else None


def _sermon_href(sermon_id: int) -> str:
    return f"/sermon?id={sermon_id}"


def _library_item_href(library_item_id: int) -> str:
    return f"/library-item?id={library_item_id}"
