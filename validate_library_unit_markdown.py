"""Validate and correct library unit markdown with Ollama.

This script walks every library item unit one at a time, sends non-empty
``content_text_markdown`` to a local Ollama model, and stores the corrected
markdown back in the same database column.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import ollama
from sqlalchemy import func, select

from app.db.models import LibraryItemUnits, LibraryItems

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5:4b"


PROMPT_TEMPLATE = """You are validating markdown content extracted from a library item.

Fix OCR, spacing, punctuation, line break, heading, list, and markdown formatting issues.
Preserve the EXACT wording from the source. Do not summarize, add commentary, add metadata,
or wrap the answer in code fences.

Return the corrected markdown content text only.

Markdown content:
{content}
"""


@dataclass(frozen=True)
class CorrectedMarkdown:
    text: str
    changed: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate library item unit markdown with Ollama and update the DB."
    )
    parser.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Ollama base URL. Default: {DEFAULT_OLLAMA_URL}",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model name. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Call Ollama and print progress without writing corrections to the DB.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing remaining units after an Ollama or DB error.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most this many units. Useful for a small test run.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="HTTP timeout in seconds for each Ollama request. Default: 300.",
    )
    return parser.parse_args()


def clean_model_response(text: str) -> str:
    """Remove common wrappers while preserving the corrected markdown body."""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    return cleaned


def correct_markdown(
    client: ollama.Client,
    *,
    model: str,
    content: str,
) -> CorrectedMarkdown:
    response = client.generate(
        model=model,
        prompt=PROMPT_TEMPLATE.format(content=content),
        stream=False,
        think=False,
        options={
            "temperature": 0,
        },
    )
    if response.response:
        corrected = clean_model_response(response.response)
    else:
        corrected = None

    if not corrected:
        raise ValueError("Ollama returned an empty correction.")

    return CorrectedMarkdown(text=corrected, changed=corrected != content)


def unit_label(unit: LibraryItemUnits) -> str:
    item = unit.library_item
    title = item.title if item is not None else "unknown item"
    return (
        f"unit_id={unit.library_item_unit_id} "
        f"item_id={unit.library_item_id} "
        f"order={unit.unit_order} "
        f"title={title!r}"
    )


def main() -> int:
    args = parse_args()

    from app.db.session import SessionLocal

    print("Starting library unit markdown validation.")
    print(f"Ollama URL: {args.ollama_url}")
    print(f"Model: {args.model}")
    print(f"Dry run: {'yes' if args.dry_run else 'no'}")

    processed = 0
    skipped = 0
    changed = 0
    unchanged = 0
    errors = 0

    with SessionLocal() as db:
        total = (
            db.scalar(
                select(func.count())
                .select_from(LibraryItemUnits)
                .where(LibraryItemUnits.library_item_id == 2)
            )
            or 0
        )
        print(f"Found {total} library item unit(s).")

        stmt = (
            select(LibraryItemUnits)
            .join(LibraryItems)
            .where(LibraryItemUnits.library_item_id == 2)
            .order_by(
                LibraryItemUnits.library_item_id,
                LibraryItemUnits.library_item_unit_id,
            )
        )
        if args.limit is not None:
            stmt = stmt.limit(args.limit)
            print(f"Limit enabled: processing at most {args.limit} unit(s).")

        client = ollama.Client(host=args.ollama_url, timeout=args.timeout)
        units = db.scalars(stmt).all()
        for index, unit in enumerate(units, start=1):
            content = unit.content_text_markdown
            label = unit_label(unit)

            print(f"[{index}/{len(units)}] Checking {label}")

            if content is None or not content.strip():
                skipped += 1
                print("  Skipped: no markdown content text.")
                continue

            try:
                print(f"  Sending to Ollama ({len(content)} character(s)).")
                corrected = correct_markdown(
                    client,
                    model=args.model,
                    content=content,
                )

                processed += 1
                if corrected.changed:
                    changed += 1
                    print(
                        "  Correction received: "
                        f"{len(content)} -> {len(corrected.text)} character(s)."
                    )
                    if args.dry_run:
                        db.rollback()
                        print("  Dry run: database not updated.")
                    else:
                        unit.content_text_markdown = corrected.text
                        db.commit()
                        print("  Updated database.")
                else:
                    unchanged += 1
                    db.rollback()
                    print("  No changes returned.")
            except Exception as exc:
                errors += 1
                db.rollback()
                print(f"  Error: {exc}", file=sys.stderr)
                if not args.continue_on_error:
                    print("Stopping because --continue-on-error was not set.")
                    break

    print("Finished library unit markdown validation.")
    print(
        "Summary: "
        f"processed={processed}, changed={changed}, unchanged={unchanged}, "
        f"skipped={skipped}, errors={errors}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
