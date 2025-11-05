import os
from types import SimpleNamespace
from unittest import mock

import django
from django.apps import apps
from django.contrib import messages
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, SimpleTestCase

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sermon_site.settings')
if not apps.ready:
    django.setup()

from archive import views  # noqa: E402  pylint: disable=wrong-import-position


class _DummyUser(SimpleNamespace):
    def __str__(self):  # pragma: no cover - simple string helper
        return getattr(self, 'username', 'widget-user')


class BibleWidgetViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = _DummyUser(is_authenticated=True, username='tester', has_perm=lambda perm: True)

    def _attach_session(self, request):
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        storage = FallbackStorage(request)
        setattr(request, '_messages', storage)

    def _make_post(self, path, data=None):
        request = self.factory.post(path, data=data or {})
        request.user = self.user
        self._attach_session(request)
        return request

    def test_add_to_widget_creates_entry_and_warns_on_length(self):
        request = self._make_post('/verses/tools', {
            'form_action': 'add_to_widget',
            'reference': 'John 3:16',
            'selected_translation': 'ESV',
        })

        long_text = 'x' * 160
        result = {
            'start_verse_id': 101,
            'end_verse_id': 101,
            'is_read_only': False,
            'selected_translation': 'ESV',
            'available_translations': ['ESV'],
            'translation_payload': {'ESV': long_text},
            'heading': 'John 3:16',
            'translation_display_payload': {'ESV': long_text},
            'note_text': '',
            'note_html': '',
            'cross_references': {
                'has_any': False,
                'items_by_verse': {},
                'active_verse_id': 101,
                'is_passage': False,
                'verse_options': [{'id': 101, 'label': 'John 3:16'}],
                'initial_items': [],
            },
            'commentaries': {
                'has_any': False,
                'count': 0,
            },
        }

        manager = mock.Mock()
        manager.update_or_create.return_value = (SimpleNamespace(weight=1), True)

        with mock.patch.object(views, '_build_related_sermons', return_value=[]), \
             mock.patch.object(views.BibleWidgetVerse, 'objects', manager), \
             mock.patch.object(views, 'BibleBook') as mock_book_model, \
             mock.patch.object(views, '_load_passage_context', return_value=(result, '')), \
             mock.patch.object(views, 'get_object_or_404', return_value=SimpleNamespace(pk=101, verse_id=101)):
            mock_book_model.objects.order_by.return_value = []
            response = views.verse_tools(request)

        self.assertEqual(response.status_code, 200)
        manager.update_or_create.assert_called_once()
        call_kwargs = manager.update_or_create.call_args.kwargs
        self.assertEqual(call_kwargs['defaults']['translation'], 'ESV')
        self.assertEqual(call_kwargs['defaults']['display_text'], long_text)

        messages_list = list(get_messages(request))
        self.assertEqual(messages_list[0].message, 'Added verse to the BibleWidget.')
        self.assertEqual(messages_list[0].level, messages.SUCCESS)
        self.assertEqual(messages_list[1].level, messages.WARNING)
        self.assertIn('155', messages_list[1].message)

    def test_add_to_widget_rejects_passage_range(self):
        request = self._make_post('/verses/tools', {
            'form_action': 'add_to_widget',
            'reference': 'John 3:16-17',
            'selected_translation': 'ESV',
        })

        result = {
            'start_verse_id': 101,
            'end_verse_id': 102,
            'is_read_only': True,
            'selected_translation': 'ESV',
            'available_translations': ['ESV'],
            'translation_payload': {'ESV': 'text'},
            'heading': 'John 3:16-17',
            'translation_display_payload': {'ESV': 'text'},
            'note_text': '',
            'note_html': '',
            'cross_references': {
                'has_any': False,
                'items_by_verse': {},
                'active_verse_id': 101,
                'is_passage': True,
                'verse_options': [
                    {'id': 101, 'label': 'John 3:16'},
                    {'id': 102, 'label': 'John 3:17'},
                ],
                'initial_items': [],
            },
            'commentaries': {
                'has_any': False,
                'count': 0,
            },
        }

        manager = mock.Mock()

        with mock.patch.object(views, '_build_related_sermons', return_value=[]), \
             mock.patch.object(views.BibleWidgetVerse, 'objects', manager), \
             mock.patch.object(views, 'BibleBook') as mock_book_model, \
             mock.patch.object(views, '_load_passage_context', return_value=(result, '')):
            mock_book_model.objects.order_by.return_value = []
            response = views.verse_tools(request)

        self.assertEqual(response.status_code, 200)
        manager.update_or_create.assert_not_called()
        messages_list = list(get_messages(request))
        self.assertIn('single verse', messages_list[0].message)
        self.assertEqual(messages_list[0].level, messages.ERROR)

    def test_weight_decrease_clamps_at_one(self):
        request = self._make_post('/verses/widget', {
            'action': 'weight_down',
            'entry_id': '7',
        })

        entry = SimpleNamespace(weight=1, ref='John 3:16', verse_id=101, save=mock.Mock(), delete=mock.Mock())

        with mock.patch.object(views, 'get_object_or_404', return_value=entry):
            response = views.bible_widget_list(request)

        self.assertEqual(response.status_code, 302)
        entry.save.assert_not_called()
        messages_list = list(get_messages(request))
        self.assertEqual(messages_list[0].message, 'Weight is already at the minimum value of 1.')
        self.assertEqual(messages_list[0].level, messages.INFO)

    def test_text_update_trims_and_saves(self):
        request = self._make_post('/verses/widget', {
            'action': 'update_text',
            'entry_id': '9',
            'display_text': '  For God so loved  ',
        })

        entry = SimpleNamespace(display_text='Original', ref='John 3:16', verse_id=101, save=mock.Mock())

        with mock.patch.object(views, 'get_object_or_404', return_value=entry):
            response = views.bible_widget_list(request)

        self.assertEqual(response.status_code, 302)
        entry.save.assert_called_once_with(update_fields=['display_text'])
        self.assertEqual(entry.display_text, 'For God so loved')
        messages_list = list(get_messages(request))
        self.assertEqual(messages_list[0].message, 'Updated display text for John 3:16.')
        self.assertEqual(messages_list[0].level, messages.SUCCESS)
