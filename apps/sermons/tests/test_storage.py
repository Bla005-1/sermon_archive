import os
from datetime import date
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import django
from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
if not apps.ready:
    django.setup()

from apps.sermons import storage  # noqa: E402  pylint: disable=wrong-import-position


class AttachmentStorageTests(SimpleTestCase):
    def test_save_attachment_file_respects_configured_root(self):
        with TemporaryDirectory() as tmpdir, override_settings(SERMON_STORAGE_ROOT=tmpdir):
            uploaded = SimpleUploadedFile('notes.txt', b'hello world')
            sermon = SimpleNamespace(preached_on=date(2024, 1, 7), id=42)

            rel_path, meta = storage.save_attachment_file(sermon, uploaded)
            abs_path = os.path.join(tmpdir, rel_path)

            self.assertTrue(os.path.exists(abs_path))
            self.assertFalse(os.path.isabs(rel_path))
            self.assertEqual(meta['byte_size'], len(b'hello world'))
            self.assertEqual(meta['mime_type'], 'text/plain')
