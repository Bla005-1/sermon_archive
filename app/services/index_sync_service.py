"""Transactional outbox and retrying dispatcher for sermon index synchronization."""

from __future__ import annotations

import datetime as dt
import logging
import threading

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import IndexSyncOperation, IndexSyncOutbox, IndexSyncStatus
from app.db.session import SessionLocal
from app.services import search_index_client

logger = logging.getLogger("sermon_archive.index_sync")
_stop = threading.Event()
_thread: threading.Thread | None = None


def enqueue(db: Session, sermon_id: int, operation: IndexSyncOperation) -> IndexSyncOutbox:
    pending = db.scalar(
        select(IndexSyncOutbox)
        .where(
            IndexSyncOutbox.sermon_id == sermon_id,
            IndexSyncOutbox.status == IndexSyncStatus.PENDING,
        )
        .order_by(IndexSyncOutbox.event_id.desc())
        .with_for_update()
    )
    if pending is not None:
        pending.operation = operation
        pending.attempt_count = 0
        pending.last_error = None
        pending.next_attempt_at = dt.datetime.now(dt.UTC).replace(tzinfo=None)
        pending.updated_at = pending.next_attempt_at
        return pending
    event = IndexSyncOutbox(sermon_id=sermon_id, operation=operation)
    db.add(event)
    db.flush()
    return event


def dispatch_once() -> bool:
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    with SessionLocal() as db:
        db.query(IndexSyncOutbox).filter(
            IndexSyncOutbox.status == IndexSyncStatus.PROCESSING,
            IndexSyncOutbox.updated_at < now - dt.timedelta(minutes=10),
        ).update(
            {
                IndexSyncOutbox.status: IndexSyncStatus.PENDING,
                IndexSyncOutbox.next_attempt_at: now,
            },
            synchronize_session=False,
        )
        db.commit()
        event = db.scalar(
            select(IndexSyncOutbox)
            .where(
                IndexSyncOutbox.status == IndexSyncStatus.PENDING,
                IndexSyncOutbox.next_attempt_at <= now,
            )
            .order_by(IndexSyncOutbox.event_id)
            .with_for_update(skip_locked=True)
        )
        if event is None:
            return False
        event.status = IndexSyncStatus.PROCESSING
        event.attempt_count += 1
        event.updated_at = now
        event_id = event.event_id
        sermon_id = event.sermon_id
        operation = event.operation
        db.commit()

    try:
        if operation == IndexSyncOperation.DELETE:
            search_index_client.delete_sermon(sermon_id)
        else:
            search_index_client.queue_sermon(sermon_id)
    except Exception as exc:
        with SessionLocal() as db:
            failed = db.get(IndexSyncOutbox, event_id)
            if failed is not None:
                failed.last_error = str(exc)
                failed.updated_at = dt.datetime.now(dt.UTC).replace(tzinfo=None)
                if failed.attempt_count >= settings.index_sync_max_attempts:
                    failed.status = IndexSyncStatus.FAILED
                else:
                    failed.status = IndexSyncStatus.PENDING
                    delay = min(300, 2 ** min(failed.attempt_count, 8))
                    failed.next_attempt_at = now + dt.timedelta(seconds=delay)
                db.commit()
        logger.warning("Index sync delivery failed event_id=%s", event_id, exc_info=True)
        return True

    with SessionLocal() as db:
        delivered = db.get(IndexSyncOutbox, event_id)
        if delivered is not None:
            delivered.status = IndexSyncStatus.DELIVERED
            delivered.last_error = None
            delivered.delivered_at = dt.datetime.now(dt.UTC).replace(tzinfo=None)
            delivered.updated_at = delivered.delivered_at
            db.commit()
    return True


def counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(IndexSyncOutbox.status, func.count()).group_by(IndexSyncOutbox.status)
    ).all()
    values = {status.value: int(count) for status, count in rows}
    return {status.value: values.get(status.value, 0) for status in IndexSyncStatus}


def start_dispatcher() -> None:
    global _thread
    if not settings.index_sync_dispatch_enabled or (_thread and _thread.is_alive()):
        return
    _stop.clear()
    _thread = threading.Thread(target=_run, name="index-sync", daemon=True)
    _thread.start()


def stop_dispatcher() -> None:
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=max(settings.index_sync_poll_seconds * 2, 1.0))


def _run() -> None:
    while not _stop.is_set():
        try:
            worked = dispatch_once()
        except Exception:
            logger.exception("Index sync dispatcher iteration failed")
            worked = False
        if not worked:
            _stop.wait(settings.index_sync_poll_seconds)
