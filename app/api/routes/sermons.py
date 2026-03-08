from fastapi import APIRouter, Depends, File, Path, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from app.schemas.attachments import Attachment
from app.schemas.sermons import (
    PatchedSermon,
    PartialSermonPassage,
    Sermon,
    SermonPassage,
    SermonSuggestionsResponse,
)
from app.services import attachment_service, sermons_service

router = APIRouter(tags=["sermons"], dependencies=[Depends(require_auth)])


@router.get("", response_model=list[Sermon], operation_id="sermons_list")
def sermons_list(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Sermon]:
    return sermons_service.list_sermons(db=db, q=q)


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
    "/{sermon_id}/passages",
    response_model=list[SermonPassage],
    operation_id="sermons_passages_list",
)
def sermons_passages_list(
    sermon_id: int = Path(...),
    db: Session = Depends(get_db),
) -> list[SermonPassage]:
    return sermons_service.list_sermon_passages(db=db, sermon_id=sermon_id)


@router.post(
    "/{sermon_id}/passages",
    response_model=SermonPassage,
    status_code=status.HTTP_201_CREATED,
    operation_id="sermons_passages_create",
)
def sermons_passages_create(
    payload: SermonPassage,
    sermon_id: int = Path(...),
    db: Session = Depends(get_db),
) -> SermonPassage:
    return sermons_service.create_sermon_passage(
        db=db, sermon_id=sermon_id, payload=payload
    )


@router.get(
    "/{sermon_id}/passages/{id}",
    response_model=SermonPassage,
    operation_id="sermons_passages_retrieve_2",
)
def sermons_passages_retrieve_2(
    sermon_id: int = Path(...),
    id: int = Path(...),
    db: Session = Depends(get_db),
) -> SermonPassage:
    return sermons_service.get_sermon_passage(db=db, sermon_id=sermon_id, passage_id=id)


@router.put(
    "/{sermon_id}/passages/{id}",
    response_model=SermonPassage,
    operation_id="sermons_passages_update_2",
)
def sermons_passages_update_2(
    payload: SermonPassage,
    sermon_id: int = Path(...),
    id: int = Path(...),
    db: Session = Depends(get_db),
) -> SermonPassage:
    return sermons_service.update_sermon_passage(
        db=db,
        sermon_id=sermon_id,
        passage_id=id,
        payload=payload,
    )


@router.patch(
    "/{sermon_id}/passages/{id}",
    response_model=SermonPassage,
    operation_id="sermons_passages_partial_update_2",
)
def sermons_passages_partial_update_2(
    payload: PartialSermonPassage,
    sermon_id: int = Path(...),
    id: int = Path(...),
    db: Session = Depends(get_db),
) -> SermonPassage:
    return sermons_service.patch_sermon_passage(
        db=db,
        sermon_id=sermon_id,
        passage_id=id,
        payload=payload,
    )


@router.delete(
    "/{sermon_id}/passages/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="sermons_passages_destroy_2",
)
def sermons_passages_destroy_2(
    sermon_id: int = Path(...),
    id: int = Path(...),
    db: Session = Depends(get_db),
) -> None:
    sermons_service.delete_sermon_passage(db=db, sermon_id=sermon_id, passage_id=id)


@router.get(
    "/suggestions",
    response_model=SermonSuggestionsResponse,
    operation_id="sermons_suggestions_retrieve",
)
def sermons_suggestions_retrieve(
    db: Session = Depends(get_db),
) -> SermonSuggestionsResponse:
    return sermons_service.get_suggestions(db=db)
