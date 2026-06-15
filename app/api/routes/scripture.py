from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from app.services import scripture_extraction_service
from sermon_archive.schemas import ScriptureExtractionRequest, ScriptureExtractionResponse

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
