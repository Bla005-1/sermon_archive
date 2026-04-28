from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from app.schemas.attachments import Attachment, PartialAttachment
from app.services import attachment_service

router = APIRouter(tags=["attachments"], dependencies=[Depends(require_auth)])


@router.get(
    "/{attachment_id}", response_model=Attachment, operation_id="attachments_retrieve"
)
def attachments_retrieve(
    attachment_id: int = Path(
        ..., description="A unique integer value identifying this attachment."
    ),
    db: Session = Depends(get_db),
) -> Attachment:
    return attachment_service.get_attachment(db=db, attachment_id=attachment_id)


@router.put(
    "/{attachment_id}", response_model=Attachment, operation_id="attachments_update"
)
def attachments_update(
    payload: Attachment,
    attachment_id: int = Path(
        ..., description="A unique integer value identifying this attachment."
    ),
    db: Session = Depends(get_db),
) -> Attachment:
    return attachment_service.update_attachment(
        db=db,
        attachment_id=attachment_id,
        payload=payload,
    )


@router.patch(
    "/{attachment_id}",
    response_model=Attachment,
    operation_id="attachments_partial_update",
)
def attachments_partial_update(
    payload: PartialAttachment,
    attachment_id: int = Path(
        ..., description="A unique integer value identifying this attachment."
    ),
    db: Session = Depends(get_db),
) -> Attachment:
    return attachment_service.patch_attachment(
        db=db,
        attachment_id=attachment_id,
        payload=payload,
    )


@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="attachments_destroy",
)
def attachments_destroy(
    attachment_id: int = Path(
        ..., description="A unique integer value identifying this attachment."
    ),
    db: Session = Depends(get_db),
) -> None:
    attachment_service.delete_attachment(db=db, attachment_id=attachment_id)
