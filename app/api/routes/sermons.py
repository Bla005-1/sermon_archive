from fastapi import APIRouter, Depends, File, Path, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from sermon_archive.schemas import (
    Attachment,
    PatchedSermon,
    Sermon,
    SermonSuggestionsResponse,
    ScriptureExtractionResponse,
    ScriptureReference,
)
from app.services import attachment_service, scripture_extraction_service, sermons_service

router = APIRouter(tags=["sermons"], dependencies=[Depends(require_auth)])


@router.get("", response_model=list[Sermon], operation_id="sermons_list")
def sermons_list(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Sermon]:
    return sermons_service.list_sermons(db=db, q=q)


@router.get(
    "/suggestions",
    response_model=SermonSuggestionsResponse,
    operation_id="sermons_suggestions_list",
)
def sermons_suggestions_list(
    db: Session = Depends(get_db),
) -> SermonSuggestionsResponse:
    return sermons_service.get_suggestions(db=db)


@router.post(
    "",
    response_model=Sermon,
    status_code=status.HTTP_201_CREATED,
    operation_id="sermons_create",
)
def sermons_create(payload: Sermon, db: Session = Depends(get_db)) -> Sermon:
    return sermons_service.create_sermon(db=db, payload=payload)


@router.get("/{sermon_id}", response_model=Sermon, operation_id="sermons_retrieve")
def sermons_retrieve(
    sermon_id: int = Path(
        ..., description="A unique integer value identifying this sermon."
    ),
    db: Session = Depends(get_db),
) -> Sermon:
    return sermons_service.get_sermon(db=db, sermon_id=sermon_id)


@router.put("/{sermon_id}", response_model=Sermon, operation_id="sermons_update")
def sermons_update(
    payload: Sermon,
    sermon_id: int = Path(
        ..., description="A unique integer value identifying this sermon."
    ),
    db: Session = Depends(get_db),
) -> Sermon:
    return sermons_service.update_sermon(db=db, sermon_id=sermon_id, payload=payload)


@router.patch(
    "/{sermon_id}", response_model=Sermon, operation_id="sermons_partial_update"
)
def sermons_partial_update(
    payload: PatchedSermon,
    sermon_id: int = Path(
        ..., description="A unique integer value identifying this sermon."
    ),
    db: Session = Depends(get_db),
) -> Sermon:
    return sermons_service.patch_sermon(db=db, sermon_id=sermon_id, payload=payload)


@router.delete(
    "/{sermon_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="sermons_destroy",
)
def sermons_destroy(
    sermon_id: int = Path(
        ..., description="A unique integer value identifying this sermon."
    ),
    db: Session = Depends(get_db),
) -> None:
    sermons_service.delete_sermon(db=db, sermon_id=sermon_id)


@router.get(
    "/{sermon_id}/attachments",
    response_model=list[Attachment],
    operation_id="sermons_attachments_list",
)
def sermons_attachments_list(
    sermon_id: int = Path(...),
    db: Session = Depends(get_db),
) -> list[Attachment]:
    return attachment_service.list_sermon_attachments(db=db, sermon_id=sermon_id)


@router.post(
    "/{sermon_id}/attachments",
    response_model=Attachment,
    status_code=status.HTTP_201_CREATED,
    operation_id="sermons_attachments_create",
)
def sermons_attachments_create(
    sermon_id: int = Path(...),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> Attachment:
    return attachment_service.create_sermon_attachment(
        db=db, sermon_id=sermon_id, file=file
    )


@router.get(
    "/{sermon_id}/attachments/{attachment_id}/download",
    operation_id="sermons_attachments_download",
)
def sermons_attachments_download(
    sermon_id: int = Path(...),
    attachment_id: int = Path(...),
    db: Session = Depends(get_db),
) -> FileResponse:
    abs_path, filename, mime_type = attachment_service.get_sermon_attachment_download(
        db=db, sermon_id=sermon_id, attachment_id=attachment_id
    )
    return FileResponse(
        path=abs_path,
        media_type=mime_type,
        filename=filename,
    )


@router.get(
    "/{sermon_id}/scripture-references",
    response_model=list[ScriptureReference],
    operation_id="sermons_scripture_references_list",
)
def sermons_scripture_references_list(
    sermon_id: int = Path(...),
    db: Session = Depends(get_db),
) -> list[ScriptureReference]:
    return scripture_extraction_service.list_sermon_references(
        db=db,
        sermon_id=sermon_id,
    )


@router.post(
    "/{sermon_id}/scripture-references/extract",
    response_model=ScriptureExtractionResponse,
    operation_id="sermons_scripture_references_extract",
)
def sermons_scripture_references_extract(
    sermon_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ScriptureExtractionResponse:
    return scripture_extraction_service.extract_sermon_references(
        db=db,
        sermon_id=sermon_id,
    )

