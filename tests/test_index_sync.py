from __future__ import annotations

from app.db.models import (
    IndexSyncOperation,
    IndexSyncOutbox,
    IndexSyncStatus,
)
from app.services import index_sync_service, search_index_client
from app.services import sermons_service
from sermon_archive.schemas import PatchedSermon, Sermon
from tests.factories import seed_user
from sqlalchemy.orm import sessionmaker


def test_pending_sermon_events_coalesce_to_latest_operation(db_session):
    first = index_sync_service.enqueue(db_session, 72, IndexSyncOperation.UPSERT)
    db_session.flush()
    event_id = first.event_id

    second = index_sync_service.enqueue(db_session, 72, IndexSyncOperation.DELETE)
    db_session.commit()

    assert second.event_id == event_id
    rows = db_session.query(IndexSyncOutbox).all()
    assert len(rows) == 1
    assert rows[0].operation == IndexSyncOperation.DELETE
    assert rows[0].status == IndexSyncStatus.PENDING


def test_processing_event_gets_one_pending_followup(db_session):
    processing = index_sync_service.enqueue(db_session, 43, IndexSyncOperation.UPSERT)
    db_session.flush()
    processing.status = IndexSyncStatus.PROCESSING
    db_session.flush()

    followup = index_sync_service.enqueue(db_session, 43, IndexSyncOperation.UPSERT)
    again = index_sync_service.enqueue(db_session, 43, IndexSyncOperation.UPSERT)
    db_session.commit()

    assert followup.event_id == again.event_id
    assert followup.event_id != processing.event_id
    assert db_session.query(IndexSyncOutbox).count() == 2


def test_search_client_always_queues_llm_forced_replacement(monkeypatch):
    seen = {}

    def fake_post(url, *, json, timeout):
        seen.update(url=url, json=json, timeout=timeout)

        class Response:
            status_code = 200
            content = b"{}"
            text = "{}"

            @staticmethod
            def json():
                return {
                    "job_id": 9,
                    "sermon_id": 72,
                    "status": "queued",
                    "stage": "queued",
                    "status_url": "/api/index/jobs/9",
                }

        return Response()

    monkeypatch.setattr(search_index_client.httpx, "post", fake_post)

    search_index_client.queue_sermon(72)

    assert seen["json"] == {"force_rebuild": True, "index_method": "llm"}


def test_sermon_create_edit_and_delete_write_transactional_outbox(db_session):
    owner = seed_user(db_session)
    created = sermons_service.create_sermon(
        db_session, Sermon(title="Queued Sermon"), owner
    )
    event = db_session.query(IndexSyncOutbox).filter_by(
        sermon_id=created.sermon_id
    ).one()
    assert event.operation == IndexSyncOperation.UPSERT

    sermons_service.patch_sermon(
        db_session,
        created.sermon_id,
        PatchedSermon(title="Queued Sermon Updated"),
        owner,
    )
    assert db_session.query(IndexSyncOutbox).filter_by(
        sermon_id=created.sermon_id
    ).count() == 1

    sermons_service.delete_sermon(db_session, created.sermon_id, owner)
    event = db_session.query(IndexSyncOutbox).filter_by(
        sermon_id=created.sermon_id
    ).one()
    assert event.operation == IndexSyncOperation.DELETE


def test_dispatcher_marks_accepted_event_delivered(db_session, monkeypatch):
    event = index_sync_service.enqueue(db_session, 71, IndexSyncOperation.UPSERT)
    db_session.commit()
    sessions = sessionmaker(bind=db_session.bind, expire_on_commit=False)
    monkeypatch.setattr(index_sync_service, "SessionLocal", sessions)
    delivered: list[int] = []
    monkeypatch.setattr(
        index_sync_service.search_index_client,
        "queue_sermon",
        lambda sermon_id: delivered.append(sermon_id) or {"job_id": 1},
    )

    assert index_sync_service.dispatch_once() is True

    db_session.expire_all()
    assert delivered == [71]
    assert db_session.get(IndexSyncOutbox, event.event_id).status == IndexSyncStatus.DELIVERED


def test_dispatcher_records_terminal_delivery_failure(db_session, monkeypatch):
    event = index_sync_service.enqueue(db_session, 43, IndexSyncOperation.UPSERT)
    db_session.commit()
    sessions = sessionmaker(bind=db_session.bind, expire_on_commit=False)
    monkeypatch.setattr(index_sync_service, "SessionLocal", sessions)
    monkeypatch.setattr(index_sync_service.settings, "index_sync_max_attempts", 1)

    def fail(_sermon_id):
        raise RuntimeError("search offline")

    monkeypatch.setattr(index_sync_service.search_index_client, "queue_sermon", fail)

    assert index_sync_service.dispatch_once() is True

    db_session.expire_all()
    failed = db_session.get(IndexSyncOutbox, event.event_id)
    assert failed.status == IndexSyncStatus.FAILED
    assert failed.last_error == "search offline"
