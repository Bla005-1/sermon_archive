from fastapi import APIRouter, Depends, File, Path, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from app.services import library_service
from sermon_archive.schemas import (
    LibraryItem,
    LibraryItemFile,
    LibraryItemUnit,
    LibraryUnitTypeEnum,
)

router = APIRouter(tags=["library"], dependencies=[Depends(require_auth)])


@router.get(
    "/items",
    response_model=list[LibraryItem],
    operation_id="library_items_list",
)
def library_items_list(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[LibraryItem]:
    return library_service.list_library_items(db=db, q=q)


@router.get(
    "/items/{library_item_id}",
    response_model=LibraryItem,
    operation_id="library_items_retrieve",
)
def library_items_retrieve(
    library_item_id: int = Path(...),
    db: Session = Depends(get_db),
) -> LibraryItem:
    return library_service.get_library_item(db=db, library_item_id=library_item_id)


@router.get(
    "/items/{library_item_id}/files",
    response_model=list[LibraryItemFile],
    operation_id="library_item_files_list",
)
def library_item_files_list(
    library_item_id: int = Path(...),
    db: Session = Depends(get_db),
) -> list[LibraryItemFile]:
    return library_service.list_library_item_files(
        db=db, library_item_id=library_item_id
    )


@router.post(
    "/items/{library_item_id}/files",
    response_model=LibraryItemFile,
    status_code=status.HTTP_201_CREATED,
    operation_id="library_item_files_create",
)
def library_item_files_create(
    library_item_id: int = Path(...),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> LibraryItemFile:
    return library_service.create_library_item_file(
        db=db, library_item_id=library_item_id, file=file
    )


@router.get(
    "/items/{library_item_id}/files/{library_item_file_id}/download",
    operation_id="library_item_files_download",
)
def library_item_files_download(
    library_item_id: int = Path(...),
    library_item_file_id: int = Path(...),
    db: Session = Depends(get_db),
) -> FileResponse:
    abs_path, filename, mime_type = library_service.get_library_item_file_response(
        db=db,
        library_item_id=library_item_id,
        library_item_file_id=library_item_file_id,
    )
    return FileResponse(path=abs_path, media_type=mime_type, filename=filename)


@router.get(
    "/items/{library_item_id}/files/{library_item_file_id}/preview",
    operation_id="library_item_files_preview",
)
def library_item_files_preview(
    library_item_id: int = Path(...),
    library_item_file_id: int = Path(...),
    db: Session = Depends(get_db),
) -> FileResponse:
    abs_path, filename, mime_type = library_service.get_library_item_file_response(
        db=db,
        library_item_id=library_item_id,
        library_item_file_id=library_item_file_id,
        preview=True,
    )
    return FileResponse(
        path=abs_path,
        media_type=mime_type,
        filename=filename,
        content_disposition_type="inline",
    )


@router.get(
    "/items/{library_item_id}/units",
    response_model=list[LibraryItemUnit],
    operation_id="library_item_units_list",
)
def library_item_units_list(
    library_item_id: int = Path(...),
    root_unit_type: LibraryUnitTypeEnum | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[LibraryItemUnit]:
    return library_service.list_library_item_units(
        db=db,
        library_item_id=library_item_id,
        root_unit_type=root_unit_type.value if root_unit_type else None,
    )
