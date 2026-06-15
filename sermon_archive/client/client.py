from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter

from sermon_archive.schemas import (
    Attachment,
    BibleWidget,
    CsrfResponse,
    LibraryItem,
    LibraryItemFile,
    LibraryItemUnit,
    LibraryUnitTypeEnum,
    LoginRequest,
    Sermon,
    SermonPassage,
    SermonSuggestionsResponse,
    PartialScriptureReference,
    ScriptureExtractionRequest,
    ScriptureExtractionResponse,
    ScriptureReference,
    ScriptureReferenceCreate,
    ScriptureReferenceSourceType,
    ScriptureReferenceUpdate,
    TokenLoginRequest,
    TokenResponse,
    TokenRevokeResponse,
    UserResponse,
    VerseNote,
    VerseQueryResponse,
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
        bearer_token: str | None = None,
        timeout: float | httpx.Timeout = 10.0,
        transport: httpx.BaseTransport | None = None,
        csrf_cookie_name: str = "csrftoken",
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
        )
        self._bearer_token = bearer_token
        self._csrf_cookie_name = csrf_cookie_name

    def __enter__(self) -> SermonArchiveClient:
        self._client.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._client.__exit__(*args)

    def close(self) -> None:
        self._client.close()

    def set_bearer_token(self, token: str | None) -> None:
        self._bearer_token = token

    def csrf(self) -> CsrfResponse:
        return self._request_model("GET", "/api/auth/csrf", CsrfResponse)

    def login(self, username: str, password: str) -> UserResponse:
        payload = LoginRequest(username=username, password=password)
        return self._request_model(
            "POST",
            "/api/auth/login",
            UserResponse,
            json=payload.model_dump(mode="json"),
            include_csrf=True,
        )

    def issue_token(
        self, username: str, password: str, token_name: str | None = None
    ) -> TokenResponse:
        payload = TokenLoginRequest(
            username=username,
            password=password,
            token_name=token_name,
        )
        return self._request_model(
            "POST",
            "/api/auth/token",
            TokenResponse,
            json=payload.model_dump(mode="json"),
            include_csrf=True,
        )

    def revoke_token(self, access_token: str | None = None) -> TokenRevokeResponse:
        return self._request_model(
            "POST",
            "/api/auth/token/revoke",
            TokenRevokeResponse,
            bearer_token=access_token,
            include_csrf=True,
        )

    def logout(self) -> None:
        self._request("POST", "/api/auth/logout", include_csrf=True)

    def me(self) -> UserResponse:
        return self._request_model("GET", "/api/auth/me", UserResponse)

    def refresh(self) -> UserResponse:
        return self._request_model(
            "POST",
            "/api/auth/refresh",
            UserResponse,
            include_csrf=True,
        )

    def list_sermons(self, q: str | None = None) -> list[Sermon]:
        params = {"q": q} if q is not None else None
        return self._request_model_list("GET", "/api/sermons", Sermon, params=params)

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

    def list_library_items(self, q: str | None = None) -> list[LibraryItem]:
        params = {"q": q} if q is not None else None
        return self._request_model_list(
            "GET",
            "/api/library/items",
            LibraryItem,
            params=params,
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

    def upload_library_item_file(
        self,
        library_item_id: int,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> LibraryItemFile:
        file_tuple = (
            (filename, content, content_type)
            if content_type
            else (filename, content)
        )
        return self._request_model(
            "POST",
            f"/api/library/items/{library_item_id}/files",
            LibraryItemFile,
            files={"file": file_tuple},
            include_csrf=True,
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

    def extract_library_item_unit_scripture_references(
        self, library_item_id: int, library_item_unit_id: int
    ) -> ScriptureExtractionResponse:
        return self._request_model(
            "POST",
            (
                f"/api/library/items/{library_item_id}/units/"
                f"{library_item_unit_id}/scripture-references/extract"
            ),
            ScriptureExtractionResponse,
            include_csrf=True,
        )

    def list_sermon_passages(self, sermon_id: int) -> list[SermonPassage]:
        return self._request_model_list(
            "GET",
            f"/api/sermons/{sermon_id}/passages",
            SermonPassage,
        )

    def get_sermon_passage(
        self, sermon_id: int, sermon_passage_id: int
    ) -> SermonPassage:
        return self._request_model(
            "GET",
            f"/api/sermons/{sermon_id}/passages/{sermon_passage_id}",
            SermonPassage,
        )

    def list_sermon_scripture_references(
        self, sermon_id: int
    ) -> list[ScriptureReference]:
        return self._request_model_list(
            "GET",
            f"/api/sermons/{sermon_id}/scripture-references",
            ScriptureReference,
        )

    def extract_sermon_scripture_references(
        self, sermon_id: int
    ) -> ScriptureExtractionResponse:
        return self._request_model(
            "POST",
            f"/api/sermons/{sermon_id}/scripture-references/extract",
            ScriptureExtractionResponse,
            include_csrf=True,
        )

    def extract_scripture_references(
        self, text: str, context_text: str | None = None
    ) -> ScriptureExtractionResponse:
        payload = ScriptureExtractionRequest(text=text, context_text=context_text)
        return self._request_model(
            "POST",
            "/api/scripture/extract",
            ScriptureExtractionResponse,
            json=payload.model_dump(mode="json"),
            include_csrf=True,
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

    def create_scripture_reference(
        self, payload: ScriptureReferenceCreate
    ) -> ScriptureReference:
        return self._request_model(
            "POST",
            "/api/scripture/references",
            ScriptureReference,
            json=payload.model_dump(mode="json"),
            include_csrf=True,
        )

    def get_scripture_reference(
        self, scripture_reference_id: int
    ) -> ScriptureReference:
        return self._request_model(
            "GET",
            f"/api/scripture/references/{scripture_reference_id}",
            ScriptureReference,
        )

    def update_scripture_reference(
        self,
        scripture_reference_id: int,
        payload: ScriptureReferenceUpdate,
    ) -> ScriptureReference:
        return self._request_model(
            "PUT",
            f"/api/scripture/references/{scripture_reference_id}",
            ScriptureReference,
            json=payload.model_dump(mode="json"),
            include_csrf=True,
        )

    def patch_scripture_reference(
        self,
        scripture_reference_id: int,
        payload: PartialScriptureReference,
    ) -> ScriptureReference:
        return self._request_model(
            "PATCH",
            f"/api/scripture/references/{scripture_reference_id}",
            ScriptureReference,
            json=payload.model_dump(mode="json", exclude_unset=True),
            include_csrf=True,
        )

    def delete_scripture_reference(self, scripture_reference_id: int) -> None:
        self._request(
            "DELETE",
            f"/api/scripture/references/{scripture_reference_id}",
            include_csrf=True,
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
    ) -> VerseQueryResponse:
        params = {"ref": reference}
        if translation is not None:
            params["translation"] = translation
        return self._request_model(
            "GET",
            "/api/verses/reference",
            VerseQueryResponse,
            params=params,
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
        bearer_token: str | None = None,
        include_csrf: bool = False,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        request_headers = self._headers(
            bearer_token=bearer_token,
            include_csrf=include_csrf,
            extra=headers,
        )
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
        bearer_token: str | None,
        include_csrf: bool,
        extra: dict[str, str] | None,
    ) -> dict[str, str]:
        headers = dict(extra or {})
        token = bearer_token if bearer_token is not None else self._bearer_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if include_csrf:
            csrf_token = self._csrf_token()
            if csrf_token:
                headers["X-CSRF-Token"] = csrf_token
        return headers

    def _csrf_token(self) -> str | None:
        value = self._client.cookies.get(self._csrf_cookie_name)
        return str(value) if value else None
