"""Library item service implementations for content, units, and files."""

from __future__ import annotations

import mimetypes
import os
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    LibraryItemFiles,
    LibraryItemUnits,
    LibraryItemUnitsUnitType,
    LibraryItems,
)
from app.services._mappers import (
    library_item_file_schema,
    library_item_schema,
    library_item_unit_schema,
)
from sermon_archive.schemas import LibraryItem, LibraryItemFile, LibraryItemUnit

PREVIEW_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _storage_root() -> str:
    """Resolve and create the base storage root used for uploaded files."""
    root = os.path.abspath(os.getenv("SERMON_STORAGE_ROOT", "."))
    os.makedirs(root, exist_ok=True)
    return root


def _safe_rel_to_abs(relative_path: str) -> str:
    """Resolve a library file relative path inside the configured storage root."""
    root = _storage_root()
    abs_path = os.path.abspath(os.path.join(root, relative_path))
    if os.path.commonpath([root, abs_path]) != root:
        raise HTTPException(
            status_code=400, detail="Library file path is outside storage root."
        )
    return abs_path


def _get_item_or_404(
    db: Session, library_item_id: int, *, include_files: bool = False
) -> LibraryItems:
    """Load a library item row or raise a 404 error."""
    stmt = select(LibraryItems).where(
        LibraryItems.library_item_id == library_item_id
    )
    if include_files:
        stmt = stmt.options(selectinload(LibraryItems.library_item_files))
    item = db.scalar(stmt)
    if item is None:
        raise HTTPException(status_code=404, detail="Library item not found.")
    return item


def _get_file_or_404(
    db: Session, library_item_id: int, library_item_file_id: int
) -> LibraryItemFiles:
    """Load one file scoped to a library item or raise a 404 error."""
    _get_item_or_404(db, library_item_id)
    file = db.scalar(
        select(LibraryItemFiles).where(
            LibraryItemFiles.library_item_id == library_item_id,
            LibraryItemFiles.library_item_file_id == library_item_file_id,
        )
    )
    if file is None:
        raise HTTPException(status_code=404, detail="Library item file not found.")
    return file


def list_library_items(db: Session, q: str | None = None) -> list[LibraryItem]:
    """Return all library items ordered by title, optionally filtered by text query."""
    stmt = (
        select(LibraryItems)
        .options(selectinload(LibraryItems.library_item_files))
        .order_by(LibraryItems.title, LibraryItems.library_item_id)
    )
    query = (q or "").strip()
    if query:
        stmt = stmt.where(
            LibraryItems.title.ilike(f"%{query}%")
            | LibraryItems.author_name.ilike(f"%{query}%")
        )
    items = db.scalars(stmt).all()
    return [library_item_schema(item, include_files=True) for item in items]


def get_library_item(db: Session, library_item_id: int) -> LibraryItem:
    """Fetch one library item with file metadata."""
    item = _get_item_or_404(db, library_item_id, include_files=True)
    return library_item_schema(item, include_files=True)


def list_library_item_files(
    db: Session, library_item_id: int
) -> list[LibraryItemFile]:
    """List files attached to a library item ordered by newest upload first."""
    _get_item_or_404(db, library_item_id)
    rows = db.scalars(
        select(LibraryItemFiles)
        .where(LibraryItemFiles.library_item_id == library_item_id)
        .order_by(
            LibraryItemFiles.created_at.desc(),
            LibraryItemFiles.library_item_file_id.desc(),
        )
    ).all()
    return [library_item_file_schema(row) for row in rows]


def create_library_item_file(
    db: Session, library_item_id: int, file: UploadFile | None
) -> LibraryItemFile:
    """Persist an uploaded file for a library item and create its metadata row."""
    _get_item_or_404(db, library_item_id)
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="Please include a file upload.")

    root = _storage_root()
    target_dir = os.path.join(root, "library", str(library_item_id))
    os.makedirs(target_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}__{os.path.basename(file.filename)}"
    abs_path = os.path.join(target_dir, stored_name)
    with open(abs_path, "wb") as handle:
        shutil.copyfileobj(file.file, handle)

    mime_type = (
        file.content_type
        or mimetypes.guess_type(file.filename)[0]
        or "application/octet-stream"
    )
    next_file_id = (
        db.scalar(select(func.max(LibraryItemFiles.library_item_file_id))) or 0
    ) + 1
    row = LibraryItemFiles(
        library_item_file_id=next_file_id,
        library_item_id=library_item_id,
        relative_path=os.path.relpath(abs_path, root),
        original_filename=file.filename,
        mime_type=mime_type,
        byte_size=os.path.getsize(abs_path),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return library_item_file_schema(row)


def get_library_item_file_response(
    db: Session,
    library_item_id: int,
    library_item_file_id: int,
    *,
    preview: bool = False,
) -> tuple[str, str, str]:
    """Resolve a library item file to an existing file and return response metadata."""
    file = _get_file_or_404(db, library_item_id, library_item_file_id)
    if not file.relative_path:
        raise HTTPException(status_code=404, detail="Library item file not found.")

    abs_path = _safe_rel_to_abs(file.relative_path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="Library item file not found.")

    filename = file.original_filename or Path(abs_path).name
    mime_type = file.mime_type or mimetypes.guess_type(filename)[0]
    mime_type = mime_type or "application/octet-stream"
    if preview and mime_type not in PREVIEW_MIME_TYPES:
        raise HTTPException(status_code=415, detail="File type cannot be previewed.")
    return abs_path, filename, mime_type


def list_library_item_units(
    db: Session, library_item_id: int, root_unit_type: str | None = None
) -> list[LibraryItemUnit]:
    """Return item units nested below top-level units or the requested root type."""
    _get_item_or_404(db, library_item_id)
    rows = db.scalars(
        select(LibraryItemUnits)
        .where(LibraryItemUnits.library_item_id == library_item_id)
        .order_by(
            LibraryItemUnits.unit_order,
            LibraryItemUnits.library_item_unit_id,
        )
    ).all()
    if not rows:
        return []

    if root_unit_type is not None:
        allowed = {unit_type.value for unit_type in LibraryItemUnitsUnitType}
        if root_unit_type not in allowed:
            raise HTTPException(status_code=400, detail="root_unit_type is invalid.")

    children_by_parent: dict[int | None, list[LibraryItemUnits]] = {}
    for row in rows:
        children_by_parent.setdefault(row.parent_library_item_unit_id, []).append(row)

    def build(row: LibraryItemUnits) -> LibraryItemUnit:
        children = [
            build(child)
            for child in children_by_parent.get(row.library_item_unit_id, [])
        ]
        return library_item_unit_schema(row, children=children)

    if root_unit_type is None:
        roots = children_by_parent.get(None, [])
    else:
        roots = [row for row in rows if row.unit_type.value == root_unit_type]

    return [build(root) for root in roots]
