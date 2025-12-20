from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest import mock

import pytest
from django.http import Http404
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.sermons import api_views as sermon_api
from apps.attachments import api_views as attachment_api


factory = APIRequestFactory()


def _authenticated_get(path: str):
    request = factory.get(path)
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
    return request


class TestSermonAttachmentDownloadView:
    """ def test_downloads_existing_file(self):
        sermon = SimpleNamespace(pk=1)
        attachment = SimpleNamespace(
            pk=2,
            rel_path="2024/1/file.txt",
            original_filename="file.txt",
            mime_type="text/plain",
        )

        with TemporaryDirectory() as tmpdir:
            abs_path = Path(tmpdir) / "file.txt"
            abs_path.write_text("content", encoding="utf-8")

            request = _authenticated_get("/api/sermons/1/attachments/2/")
            with mock.patch.object(sermon_api, "get_object_or_404", side_effect=[sermon, attachment]), \
                 mock.patch.object(sermon_api, "resolve_attachment_path", return_value=str(abs_path)):
                response = sermon_api.AttachmentDownloadView.as_view()(request, sermon_id=1, pk=2)

        assert response.status_code == 200
        assert response["Content-Disposition"].startswith('attachment; filename="file.txt"')
        assert response["Content-Type"] == "text/plain" """

    def test_raises_not_found_for_missing_file(self):
        sermon = SimpleNamespace(pk=1)
        attachment = SimpleNamespace(pk=2, rel_path="missing.bin", original_filename="missing.bin", mime_type=None)
        request = _authenticated_get("/api/sermons/1/attachments/2/")

        with mock.patch.object(sermon_api, "get_object_or_404", side_effect=[sermon, attachment]), \
             mock.patch.object(sermon_api, "resolve_attachment_path", return_value="/tmp/missing.bin"), \
             mock.patch.object(sermon_api.os.path, "exists", return_value=False):
            with pytest.raises(Http404):
                sermon_api.AttachmentDownloadView.as_view()(request, sermon_id=1, pk=2)

    def test_blocked_when_storage_resolution_fails(self):
        sermon = SimpleNamespace(pk=1)
        attachment = SimpleNamespace(pk=2, rel_path="bad.bin", original_filename=None, mime_type=None)
        request = _authenticated_get("/api/sermons/1/attachments/2/")

        with mock.patch.object(sermon_api, "get_object_or_404", side_effect=[sermon, attachment]), \
             mock.patch.object(sermon_api, "resolve_attachment_path", side_effect=sermon_api.AttachmentStorageError("nope")):
            with pytest.raises(Http404):
                sermon_api.AttachmentDownloadView.as_view()(request, sermon_id=1, pk=2)

""" 
class TestAttachmentAppDownloadView:
    def test_downloads_file_for_direct_attachment_endpoint(self):
        attachment = SimpleNamespace(
            pk=5,
            rel_path="attachments/5.bin",
            original_filename="5.bin",
            mime_type="application/octet-stream",
            sermon_id=11,
        )
        sermon = SimpleNamespace(pk=11)

        with TemporaryDirectory() as tmpdir:
            abs_path = Path(tmpdir) / "5.bin"
            abs_path.write_text("payload", encoding="utf-8")

            request = _authenticated_get("/api/attachments/5/")
            with mock.patch.object(attachment_api, "get_object_or_404", side_effect=[attachment, sermon]), \
                 mock.patch.object(attachment_api, "resolve_attachment_path", return_value=str(abs_path)):
                response = attachment_api.AttachmentDownloadView.as_view()(request, pk=5)

        assert response.status_code == 200
        assert response["Content-Disposition"].startswith('attachment; filename="5.bin"')
        assert response["Content-Type"] == "application/octet-stream"
 """