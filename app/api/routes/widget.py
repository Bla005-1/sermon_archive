from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from app.schemas.widget import BibleWidget, PartialBibleWidget
from app.services import widget_Service

router = APIRouter(tags=["widget"])


@router.get("", response_model=list[BibleWidget], operation_id="widget_list")
def widget_list(db: Session = Depends(get_db)) -> list[BibleWidget]:
    return widget_Service.list_widgets(db=db)


@router.post(
    "",
    response_model=BibleWidget,
    status_code=status.HTTP_201_CREATED,
    operation_id="widget_create",
    dependencies=[Depends(require_auth)],
)
def widget_create(payload: BibleWidget, db: Session = Depends(get_db)) -> BibleWidget:
    return widget_Service.create_widget(db=db, payload=payload)


@router.get(
    "/{widget_passage_id}", response_model=BibleWidget, operation_id="widget_retrieve"
)
def widget_retrieve(
    widget_passage_id: int = Path(...), db: Session = Depends(get_db)
) -> BibleWidget:
    return widget_Service.get_widget(db=db, widget_id=widget_passage_id)


@router.put(
    "/{widget_passage_id}",
    response_model=BibleWidget,
    operation_id="widget_update",
    dependencies=[Depends(require_auth)],
)
def widget_update(
    payload: BibleWidget,
    widget_passage_id: int = Path(...),
    db: Session = Depends(get_db),
) -> BibleWidget:
    return widget_Service.update_widget(
        db=db,
        widget_id=widget_passage_id,
        payload=payload,
    )


@router.patch(
    "/{widget_passage_id}",
    response_model=BibleWidget,
    operation_id="widget_partial_update",
    dependencies=[Depends(require_auth)],
)
def widget_partial_update(
    payload: PartialBibleWidget,
    widget_passage_id: int = Path(...),
    db: Session = Depends(get_db),
) -> BibleWidget:
    return widget_Service.patch_widget(
        db=db,
        widget_id=widget_passage_id,
        payload=payload,
    )


@router.delete(
    "/{widget_passage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="widget_destroy",
    dependencies=[Depends(require_auth)],
)
def widget_destroy(
    widget_passage_id: int = Path(...), db: Session = Depends(get_db)
) -> None:
    widget_Service.delete_widget(db=db, widget_id=widget_passage_id)
