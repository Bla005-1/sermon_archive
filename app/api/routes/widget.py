from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth_placeholder
from app.schemas.widget import BibleWidget, PatchedBibleWidget
from app.services import widget_Service

router = APIRouter(tags=["widget"], dependencies=[Depends(require_auth_placeholder)])


@router.get("/", response_model=list[BibleWidget], operation_id="widget_list")
def widget_list(db: Session = Depends(get_db)) -> list[BibleWidget]:
    return widget_Service.list_widgets(db=db)


@router.post("/", response_model=BibleWidget, status_code=status.HTTP_201_CREATED, operation_id="widget_create")
def widget_create(payload: BibleWidget, db: Session = Depends(get_db)) -> BibleWidget:
    return widget_Service.create_widget(db=db, payload=payload)


@router.get("/{id}/", response_model=BibleWidget, operation_id="widget_retrieve")
def widget_retrieve(id: int = Path(...), db: Session = Depends(get_db)) -> BibleWidget:
    return widget_Service.get_widget(db=db, widget_id=id)


@router.put("/{id}/", response_model=BibleWidget, operation_id="widget_update")
def widget_update(payload: BibleWidget, id: int = Path(...), db: Session = Depends(get_db)) -> BibleWidget:
    return widget_Service.update_widget(db=db, widget_id=id, payload=payload)


@router.patch("/{id}/", response_model=BibleWidget, operation_id="widget_partial_update")
def widget_partial_update(
    payload: PatchedBibleWidget,
    id: int = Path(...),
    db: Session = Depends(get_db),
) -> BibleWidget:
    return widget_Service.patch_widget(db=db, widget_id=id, payload=payload)


@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT, operation_id="widget_destroy")
def widget_destroy(id: int = Path(...), db: Session = Depends(get_db)) -> None:
    widget_Service.delete_widget(db=db, widget_id=id)
