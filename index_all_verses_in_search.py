"""Backfill verse and commentary search documents one Bible chapter at a time.

Run with:

    uv run --group backend python index_all_verses_in_search.py

By default the script uses SERMON_SEARCH_HOST and SERMON_SEARCH_PORT from .env,
indexes ESV chapters, and includes both verse and commentary documents.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.models import BibleBooks, BibleVerses, VerseTexts


@dataclass(frozen=True)
class ChapterReference:
    book: str
    chapter: int

    @property
    def reference(self) -> str:
        return f"{self.book} {self.chapter}"


def load_env_file(path: Path = Path(".env")) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def env_value(env: dict[str, str], key: str, default: str | None = None) -> str | None:
    return os.environ.get(key) or env.get(key) or default


def parse_args() -> argparse.Namespace:
    env = load_env_file()
    parser = argparse.ArgumentParser(
        description="Index all Bible chapters into sermon_search via /api/index/references."
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Sermon search base URL. Defaults to SERMON_SEARCH_HOST and "
            "SERMON_SEARCH_PORT from .env."
        ),
    )
    parser.add_argument(
        "--translation",
        default="ESV",
        help="Verse translation to index. Use an empty string to omit translation.",
    )
    parser.add_argument(
        "--no-commentary",
        action="store_true",
        help="Index verse documents only.",
    )
    parser.add_argument(
        "--no-verses",
        action="store_true",
        help="Index commentary documents only.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="HTTP timeout per chapter request in seconds.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Optional pause between successful chapter requests in seconds.",
    )
    parser.add_argument(
        "--start-after",
        default=None,
        help='Skip chapters through this reference, for example "John 3".',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of chapters to index.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep indexing after a failed chapter request.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the references that would be indexed without posting them.",
    )
    args = parser.parse_args()
    args.env = env
    return args


def search_base_url(raw_base_url: str | None, env: dict[str, str]) -> str:
    if raw_base_url:
        base_url = raw_base_url.strip()
    else:
        host = env_value(env, "SERMON_SEARCH_HOST", "localhost")
        port = env_value(env, "SERMON_SEARCH_PORT", "8051")
        base_url = f"http://{host}:{port}"
    return base_url.rstrip("/")


def database_url(env: dict[str, str]) -> str:
    value = env_value(env, "DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is not set in the environment or .env.")
    return value


def normalize_translation(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def load_chapters(db: Session, translation: str | None) -> list[ChapterReference]:
    statement = (
        select(BibleBooks.book_name, BibleVerses.chapter_number)
        .join(BibleVerses, BibleVerses.book_id == BibleBooks.book_id)
        .group_by(
            BibleBooks.book_order, BibleBooks.book_name, BibleVerses.chapter_number
        )
        .order_by(BibleBooks.book_order, BibleVerses.chapter_number)
    )
    if translation:
        statement = statement.join(
            VerseTexts, VerseTexts.verse_id == BibleVerses.verse_id
        ).where(func.upper(VerseTexts.translation) == translation.upper())

    rows = db.execute(statement).all()
    return [
        ChapterReference(book=row.book_name, chapter=row.chapter_number) for row in rows
    ]


def available_translations(db: Session) -> list[str]:
    statement = (
        select(VerseTexts.translation)
        .where(VerseTexts.translation.is_not(None), VerseTexts.translation != "")
        .distinct()
        .order_by(func.lower(VerseTexts.translation))
    )
    return list(db.execute(statement).scalars())


def apply_start_after(
    chapters: list[ChapterReference], start_after: str | None
) -> list[ChapterReference]:
    if not start_after:
        return chapters

    normalized = start_after.strip().lower()
    for index, chapter in enumerate(chapters):
        if chapter.reference.lower() == normalized:
            return chapters[index + 1 :]

    raise ValueError(f"--start-after did not match a loaded chapter: {start_after!r}")


def post_reference(
    client: httpx.Client,
    *,
    reference: str,
    translation: str | None,
    include_verses: bool,
    include_commentary: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "reference": reference,
        "include_verses": include_verses,
        "include_commentary": include_commentary,
    }
    if translation:
        payload["translation"] = translation

    response = client.post("/api/index/references", json=payload)
    response.raise_for_status()
    return response.json()


def main() -> int:
    args = parse_args()
    env = args.env
    translation = normalize_translation(args.translation)
    include_verses = not args.no_verses
    include_commentary = not args.no_commentary

    if not include_verses and not include_commentary:
        print(
            "Nothing to index: both --no-verses and --no-commentary were set.",
            file=sys.stderr,
        )
        return 2

    try:
        engine = create_engine(database_url(env), pool_pre_ping=True)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    with Session(engine) as db:
        chapters = load_chapters(db, translation)
        if not chapters:
            translations = ", ".join(available_translations(db)) or "none"
            print(
                f"No chapters found for translation {translation!r}. "
                f"Available translations: {translations}",
                file=sys.stderr,
            )
            return 1

    try:
        chapters = apply_start_after(chapters, args.start_after)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.limit is not None:
        chapters = chapters[: args.limit]

    base_url = search_base_url(args.base_url, env)
    total_chapters = len(chapters)
    totals: dict[str, int] = {}
    failures: list[tuple[str, str]] = []

    print(
        f"Indexing {total_chapters} chapters at {base_url} "
        f"translation={translation or '(backend default)'} "
        f"include_verses={include_verses} include_commentary={include_commentary}"
    )

    if args.dry_run:
        for chapter in chapters:
            print(chapter.reference)
        return 0

    with httpx.Client(base_url=base_url, timeout=args.timeout) as client:
        for index, chapter in enumerate(chapters, start=1):
            try:
                result = post_reference(
                    client,
                    reference=chapter.reference,
                    translation=translation,
                    include_verses=include_verses,
                    include_commentary=include_commentary,
                )
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text.strip()
                message = f"HTTP {exc.response.status_code}: {detail}"
                failures.append((chapter.reference, message))
                print(
                    f"[{index}/{total_chapters}] {chapter.reference}: FAILED {message}"
                )
                if not args.continue_on_error:
                    break
                continue
            except httpx.HTTPError as exc:
                failures.append((chapter.reference, str(exc)))
                print(f"[{index}/{total_chapters}] {chapter.reference}: FAILED {exc}")
                if not args.continue_on_error:
                    break
                continue

            indexed = result.get("indexed", {})
            for domain, count in indexed.items():
                totals[domain] = totals.get(domain, 0) + int(count)

            skipped = result.get("skipped") or []
            skipped_suffix = f" skipped={len(skipped)}" if skipped else ""
            indexed_summary = ", ".join(
                f"{domain}={count}" for domain, count in sorted(indexed.items())
            )
            print(
                f"[{index}/{total_chapters}] {chapter.reference}: "
                f"{indexed_summary or 'indexed=0'}{skipped_suffix}"
            )

            if args.delay > 0:
                time.sleep(args.delay)

    print(
        "Totals: "
        + (", ".join(f"{k}={v}" for k, v in sorted(totals.items())) or "none")
    )
    if failures:
        print("Failures:", file=sys.stderr)
        for reference, message in failures:
            print(f"  {reference}: {message}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
