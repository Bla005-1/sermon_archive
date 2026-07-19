"""HTTP client for indexing and audit operations in sermon-search."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings


def request(
    method: str,
    path: str,
    *,
    params: list[tuple[str, str]] | dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> Any:
    base_url = f"http://{settings.sermon_search_host}:{settings.sermon_search_port}"
    try:
        kwargs: dict[str, Any] = {
            "timeout": max(settings.sermon_search_timeout_seconds, 7.0)
        }
        if params is not None:
            kwargs["params"] = params
        if json is not None:
            kwargs["json"] = json
        request_method = getattr(httpx, method.lower())
        response = request_method(f"{base_url}{path}", **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Sermon search is unavailable: {exc}") from exc
    if response.status_code >= 400:
        detail: Any
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise HTTPException(status_code=502, detail=f"Sermon search error: {detail}")
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


def queue_sermon(sermon_id: int) -> dict[str, Any]:
    return request(
        "POST",
        f"/api/index/sermons/{sermon_id}",
        json={"force_rebuild": True, "index_method": "llm"},
    )


def delete_sermon(sermon_id: int) -> dict[str, Any]:
    return request("DELETE", f"/api/index/sermons/{sermon_id}")


def rebuild() -> dict[str, Any]:
    return request(
        "POST", "/api/index/rebuild", json={"full": True, "index_method": "llm"}
    )
