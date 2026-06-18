"""Normalize library section unit titles to title case."""

from __future__ import annotations

import re

from sqlalchemy import select

from app.db.models import LibraryItemUnits, LibraryItemUnitsUnitType
from app.db.session import SessionLocal

WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def title_case(value: str) -> str:
    """Convert an all-caps style heading to readable title case."""
    lowered = value.lower()
    return WORD_RE.sub(lambda match: match.group(0).capitalize(), lowered)


def main() -> None:
    updated = 0
    with SessionLocal() as db:
        units = db.scalars(
            select(LibraryItemUnits)
            .where(
                LibraryItemUnits.unit_type == LibraryItemUnitsUnitType.SECTION,
                LibraryItemUnits.unit_title.is_not(None),
            )
            .order_by(LibraryItemUnits.library_item_unit_id)
        ).all()

        for unit in units:
            original = unit.unit_title or ""
            if not original.strip():
                continue
            normalized = title_case(original)
            if normalized != original:
                unit.unit_title = normalized
                updated += 1

        db.commit()

    print(f"updated={updated}")


if __name__ == "__main__":
    main()
