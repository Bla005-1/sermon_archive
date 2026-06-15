from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from app.services import scripture_extraction_service
from sermon_archive.schemas import (
    PartialScriptureReference,
    ScriptureExtractionRequest,
    ScriptureExtractionResponse,
    ScriptureReference,
    ScriptureReferenceCreate,
    ScriptureReferenceSourceType,
    ScriptureReferenceUpdate,
)

router = APIRouter(tags=["scripture"], dependencies=[Depends(require_auth)])


@router.post(
    "/extract",
    response_model=ScriptureExtractionResponse,
    operation_id="scripture_extract",
)
def scripture_extract(
    payload: ScriptureExtractionRequest,
    db: Session = Depends(get_db),
) -> ScriptureExtractionResponse:
    return scripture_extraction_service.preview_extraction(db=db, payload=payload)


@router.get(
    "/references",
    response_model=list[ScriptureReference],
    operation_id="scripture_references_list",
)
def scripture_references_list(
    source_type: ScriptureReferenceSourceType = Query(...),
    source_id: int = Query(...),
    db: Session = Depends(get_db),
) -> list[ScriptureReference]:
    return scripture_extraction_service.list_scripture_references_for_source(
        db=db,
        source_type=source_type,
        source_id=source_id,
    )


@router.post(
    "/references",
    response_model=ScriptureReference,
    status_code=status.HTTP_201_CREATED,
    operation_id="scripture_references_create",
)
def scripture_references_create(
    payload: ScriptureReferenceCreate,
    db: Session = Depends(get_db),
) -> ScriptureReference:
    return scripture_extraction_service.create_scripture_reference(
        db=db,
        payload=payload,
    )


@router.get(
    "/references/{scripture_reference_id}",
    response_model=ScriptureReference,
    operation_id="scripture_references_retrieve",
)
def scripture_references_retrieve(
    scripture_reference_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ScriptureReference:
    return scripture_extraction_service.get_scripture_reference(
        db=db,
        scripture_reference_id=scripture_reference_id,
    )


@router.put(
    "/references/{scripture_reference_id}",
    response_model=ScriptureReference,
    operation_id="scripture_references_update",
)
def scripture_references_update(
    payload: ScriptureReferenceUpdate,
    scripture_reference_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ScriptureReference:
    return scripture_extraction_service.update_scripture_reference(
        db=db,
        scripture_reference_id=scripture_reference_id,
        payload=payload,
    )


@router.patch(
    "/references/{scripture_reference_id}",
    response_model=ScriptureReference,
    operation_id="scripture_references_partial_update",
)
def scripture_references_partial_update(
    payload: PartialScriptureReference,
    scripture_reference_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ScriptureReference:
    return scripture_extraction_service.patch_scripture_reference(
        db=db,
        scripture_reference_id=scripture_reference_id,
        payload=payload,
    )


@router.delete(
    "/references/{scripture_reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="scripture_references_destroy",
)
def scripture_references_destroy(
    scripture_reference_id: int = Path(...),
    db: Session = Depends(get_db),
) -> None:
    scripture_extraction_service.delete_scripture_reference(
        db=db,
        scripture_reference_id=scripture_reference_id,
    )
