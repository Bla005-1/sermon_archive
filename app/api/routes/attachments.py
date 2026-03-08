from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from app.schemas.attachments import Attachment, PartialAttachment
from app.services import attachment_service

router = APIRouter(tags=["attachments"], dependencies=[Depends(require_auth)])


@router.get("/{id}", response_model=Attachment, operation_id="attachments_retrieve")
def attachments_retrieve(
    id: int = Path(
        ..., description="A unique integer value identifying this attachment."
    ),
    db: Session = Depends(get_db),
) -> Attachment:
    return attachment_service.get_attachment(db=db, attachment_id=id)


@router.put("/{id}", response_model=Attachment, operation_id="attachments_update")
def attachments_update(
    payload: Attachment,
    id: int = Path(
        ..., description="A unique integer value identifying this attachment."
    ),
    db: Session = Depends(get_db),
) -> Attachment:
    return attachment_service.update_attachment(
        db=db, attachment_id=id, payload=payload
    )


@router.patch(
    "/{id}", response_model=Attachment, operation_id="attachments_partial_update"
)
def attachments_partial_update(
    payload: PartialAttachment,
    id: int = Path(
        ..., description="A unique integer value identifying this attachment."
    ),
    db: Session = Depends(get_db),
) -> Attachment:
    return attachment_service.patch_attachment(db=db, attachment_id=id, payload=payload)


@router.delete(
    "/{id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="attachments_destroy"
)
def attachments_destroy(
    id: int = Path(
        ..., description="A unique integer value identifying this attachment."
    ),
    db: Session = Depends(get_db),
) -> None:
    attachment_service.delete_attachment(db=db, attachment_id=id)
