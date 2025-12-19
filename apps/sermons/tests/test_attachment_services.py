from types import SimpleNamespace
from unittest import mock

import pytest

from apps.sermons import storage
from apps.sermons.services import attachments


class TestUploadAttachment:
    def test_upload_attachment_saves_metadata_and_returns_attachment(self, tmp_path):
        sermon = SimpleNamespace()
        uploaded = SimpleNamespace(name="slides.pdf")
        meta = {"mime_type": "application/pdf", "byte_size": 128}
        attachment = SimpleNamespace(pk=99)

        with mock.patch.object(storage, "save_attachment_file", return_value=("2024/1/file.pdf", meta)), \
             mock.patch.object(attachments.Attachment.objects, "create", return_value=attachment) as create_mock:
            saved, returned_meta = attachments.upload_attachment(sermon, uploaded)

        create_mock.assert_called_once_with(
            sermon=sermon,
            rel_path="2024/1/file.pdf",
            original_filename="slides.pdf",
            mime_type="application/pdf",
            byte_size=128,
        )
        assert saved is attachment
        assert returned_meta == meta

    def test_upload_attachment_wraps_storage_errors(self):
        sermon = SimpleNamespace()
        uploaded = SimpleNamespace(name="bad.bin")

        with mock.patch.object(storage, "save_attachment_file", side_effect=storage.AttachmentStorageError("boom")):
            with pytest.raises(attachments.AttachmentServiceError) as excinfo:
                attachments.upload_attachment(sermon, uploaded)

        assert "boom" in str(excinfo.value)

    def test_upload_attachment_surfaces_database_errors(self):
        sermon = SimpleNamespace()
        uploaded = SimpleNamespace(name="slides.pdf")
        meta = {"mime_type": "application/pdf", "byte_size": 128}

        with mock.patch.object(storage, "save_attachment_file", return_value=("2024/1/file.pdf", meta)), \
             mock.patch.object(attachments.Attachment.objects, "create", side_effect=attachments.DatabaseError("db")):
            with pytest.raises(attachments.AttachmentPersistenceError):
                attachments.upload_attachment(sermon, uploaded)


class TestDeleteAttachment:
    def test_delete_attachment_filters_by_sermon(self):
        manager = mock.Mock()
        manager.filter.return_value.delete.return_value = (1, {})
        sermon = SimpleNamespace(pk=1)

        with mock.patch.object(attachments.Attachment, "objects", manager):
            deleted = attachments.delete_attachment(sermon, 7)

        manager.filter.assert_called_once_with(sermon=sermon, pk=7)
        assert deleted == 1
