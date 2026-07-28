from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter

from sermon_archive.schemas import (
    Attachment,
    BibleWidget,
    LibraryItem,
    LibraryItemFile,
    LibraryItemListResponse,
    LibraryItemUnit,
    LibraryUnitTypeEnum,
    Sermon,
    SermonBrowseListResponse,
    SermonBrowseType,
    SermonListResponse,
    SermonSuggestionsResponse,
    ScriptureReference,
    ScriptureReferenceSourceType,
    UserResponse,
    VerseCommentaryResponse,
    VerseLibraryItemReferenceResponse,
    VerseNote,
    VerseReferenceResponse,
    VerseSermonResponse,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class SermonArchiveClientError(Exception):
    """Raised when the Sermon Archive API returns an unsuccessful response."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.status_code = response.status_code
        self.body = self._response_body(response)
        self.detail = self._response_detail(self.body)
        message = f"Sermon Archive API request failed with status {self.status_code}"
        if self.detail:
            message = f"{message}: {self.detail}"
        super().__init__(message)

    @staticmethod
    def _response_body(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _response_detail(body: Any) -> str | None:
        if isinstance(body, dict):
            detail = body.get("detail")
            if isinstance(detail, str):
                return detail
            if detail is not None:
                return str(detail)
        if isinstance(body, str) and body:
            return body
        return None


class SermonArchiveClient:
    """Small sync client for the Sermon Archive API."""

    def __init__(
        self,
        base_url: str,
        *,
        bearer_token: str,
        timeout: float | httpx.Timeout = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not bearer_token.strip():
            raise ValueError("bearer_token is required.")
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
        )
        self._bearer_token = bearer_token

    def __enter__(self) -> SermonArchiveClient:
        self._client.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._client.__exit__(*args)

    def close(self) -> None:
        self._client.close()

    def set_bearer_token(self, token: str) -> None:
        if not token.strip():
            raise ValueError("bearer token is required.")
        self._bearer_token = token

    def me(self) -> UserResponse:
        return self._request_model("GET", "/api/auth/me", UserResponse)

    def list_sermons(
        self,
        q: str | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> SermonListResponse:
        params: dict[str, str | int] = {}
        if q is not None:
            params["q"] = q
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return self._request_model(
            "GET",
            "/api/sermons",
            SermonListResponse,
            params=params or None,
        )

    def browse_sermons(
        self,
        type: SermonBrowseType | str,  # noqa: A002
        *,
        year: int | None = None,
        speaker: str | None = None,
        series: str | None = None,
        location: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> SermonBrowseListResponse:
        value = type.value if isinstance(type, SermonBrowseType) else type
        params: dict[str, str | int] = {"type": value}
        if year is not None:
            params["year"] = year
        if speaker is not None:
            params["speaker"] = speaker
        if series is not None:
            params["series"] = series
        if location is not None:
            params["location"] = location
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return self._request_model(
            "GET",
            "/api/sermons/browse",
            SermonBrowseListResponse,
            params=params,
        )

    def get_sermon(self, sermon_id: int) -> Sermon:
        return self._request_model("GET", f"/api/sermons/{sermon_id}", Sermon)

    def get_sermon_suggestions(self) -> SermonSuggestionsResponse:
        return self._request_model(
            "GET",
            "/api/sermons/suggestions",
            SermonSuggestionsResponse,
        )

    def list_sermon_attachments(self, sermon_id: int) -> list[Attachment]:
        return self._request_model_list(
            "GET",
            f"/api/sermons/{sermon_id}/attachments",
            Attachment,
        )

    def get_attachment(self, attachment_id: int) -> Attachment:
        return self._request_model(
            "GET",
            f"/api/attachments/{attachment_id}",
            Attachment,
        )

    def list_library_items(
        self,
        q: str | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> LibraryItemListResponse:
        params: dict[str, str | int] = {}
        if q is not None:
            params["q"] = q
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return self._request_model(
            "GET",
            "/api/library/items",
            LibraryItemListResponse,
            params=params or None,
        )

    def get_library_item(self, library_item_id: int) -> LibraryItem:
        return self._request_model(
            "GET",
            f"/api/library/items/{library_item_id}",
            LibraryItem,
        )

    def list_library_item_files(
        self, library_item_id: int
    ) -> list[LibraryItemFile]:
        return self._request_model_list(
            "GET",
            f"/api/library/items/{library_item_id}/files",
            LibraryItemFile,
        )

    def download_library_item_file(
        self, library_item_id: int, library_item_file_id: int
    ) -> bytes:
        response = self._request(
            "GET",
            f"/api/library/items/{library_item_id}/files/{library_item_file_id}/download",
        )
        return response.content

    def preview_library_item_file(
        self, library_item_id: int, library_item_file_id: int
    ) -> bytes:
        response = self._request(
            "GET",
            f"/api/library/items/{library_item_id}/files/{library_item_file_id}/preview",
        )
        return response.content

    def list_library_item_units(
        self,
        library_item_id: int,
        root_unit_type: LibraryUnitTypeEnum | str | None = None,
    ) -> list[LibraryItemUnit]:
        params = None
        if root_unit_type is not None:
            value = (
                root_unit_type.value
                if isinstance(root_unit_type, LibraryUnitTypeEnum)
                else root_unit_type
            )
            params = {"root_unit_type": value}
        return self._request_model_list(
            "GET",
            f"/api/library/items/{library_item_id}/units",
            LibraryItemUnit,
            params=params,
        )

    def list_library_item_unit_scripture_references(
        self, library_item_id: int, library_item_unit_id: int
    ) -> list[ScriptureReference]:
        return self._request_model_list(
            "GET",
            (
                f"/api/library/items/{library_item_id}/units/"
                f"{library_item_unit_id}/scripture-references"
            ),
            ScriptureReference,
        )

    def list_sermon_scripture_references(
        self, sermon_id: int
    ) -> list[ScriptureReference]:
        return self._request_model_list(
            "GET",
            f"/api/sermons/{sermon_id}/scripture-references",
            ScriptureReference,
        )

    def list_scripture_references(
        self,
        source_type: ScriptureReferenceSourceType | str,
        source_id: int,
    ) -> list[ScriptureReference]:
        value = (
            source_type.value
            if isinstance(source_type, ScriptureReferenceSourceType)
            else source_type
        )
        return self._request_model_list(
            "GET",
            "/api/scripture/references",
            ScriptureReference,
            params={"source_type": value, "source_id": source_id},
        )

    def get_scripture_reference(
        self, scripture_reference_id: int
    ) -> ScriptureReference:
        return self._request_model(
            "GET",
            f"/api/scripture/references/{scripture_reference_id}",
            ScriptureReference,
        )

    def list_verse_notes(self, verse_id: int | None = None) -> list[VerseNote]:
        params = {"verse_id": verse_id} if verse_id is not None else None
        return self._request_model_list(
            "GET",
            "/api/verses/notes",
            VerseNote,
            params=params,
        )

    def get_verse_note(self, note_id: int) -> VerseNote:
        return self._request_model("GET", f"/api/verses/notes/{note_id}", VerseNote)

    def get_verse(
        self, reference: str, translation: str | None = None
    ) -> VerseReferenceResponse:
        params = {"ref": reference}
        if translation is not None:
            params["translation"] = translation
        return self._request_model(
            "GET",
            "/api/verses/reference",
            VerseReferenceResponse,
            params=params,
        )

    def get_sermons_for_reference(self, reference: str) -> VerseSermonResponse:
        return self._request_model(
            "GET",
            "/api/verses/sermons",
            VerseSermonResponse,
            params={"ref": reference},
        )

    def get_commentaries_for_reference(
        self, reference: str
    ) -> VerseCommentaryResponse:
        return self._request_model(
            "GET",
            "/api/verses/commentaries",
            VerseCommentaryResponse,
            params={"ref": reference},
        )

    def get_library_items_for_reference(
        self, reference: str
    ) -> VerseLibraryItemReferenceResponse:
        return self._request_model(
            "GET",
            "/api/verses/library-items",
            VerseLibraryItemReferenceResponse,
            params={"ref": reference},
        )

    def list_widgets(self) -> list[BibleWidget]:
        return self._request_model_list("GET", "/api/widget", BibleWidget)

    def get_widget(self, widget_passage_id: int) -> BibleWidget:
        return self._request_model(
            "GET",
            f"/api/widget/{widget_passage_id}",
            BibleWidget,
        )

    def _request_model(
        self,
        method: str,
        path: str,
        model: type[ModelT],
        **kwargs: Any,
    ) -> ModelT:
        response = self._request(method, path, **kwargs)
        return model.model_validate(response.json())

    def _request_model_list(
        self,
        method: str,
        path: str,
        model: type[ModelT],
        **kwargs: Any,
    ) -> list[ModelT]:
        response = self._request(method, path, **kwargs)
        return TypeAdapter(list[model]).validate_python(response.json())

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        request_headers = self._headers(extra=headers)
        response = self._client.request(
            method,
            path,
            headers=request_headers,
            **kwargs,
        )
        if response.is_error:
            raise SermonArchiveClientError(response)
        return response

    def _headers(
        self,
        *,
        extra: dict[str, str] | None,
    ) -> dict[str, str]:
        headers = dict(extra or {})
        headers["Authorization"] = f"Bearer {self._bearer_token}"
        return headers
