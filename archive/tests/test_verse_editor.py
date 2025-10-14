import os
from datetime import date
from types import SimpleNamespace
import unittest

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sermon_site.settings')
django.setup()

from archive import views


class VerseEditorHelperTests(unittest.TestCase):
    def test_determine_available_translations_filters_incomplete_sets(self):
        verse_ids = [1, 2]
        translation_map = {
            'NIV': {1: 'For God so loved', 2: 'For God did not send'},
            'ESV': {1: 'For God so loved'},
            'KJV': {1: 'For God so loved', 2: 'For God sent not'},
        }

        available = views._determine_available_translations(verse_ids, translation_map)

        self.assertEqual(available, ['NIV', 'KJV'])

    def test_select_default_translation_prefers_configured_order(self):
        self.assertEqual(views._select_default_translation(['ESV', 'KJV']), 'ESV')
        self.assertEqual(views._select_default_translation(['KJV', 'NLT']), 'KJV')
        self.assertIsNone(views._select_default_translation([]))

    def test_join_passage_text_returns_plain_and_display_versions(self):
        verses = [
            SimpleNamespace(verse_id=1, verse=16),
            SimpleNamespace(verse_id=2, verse=17),
        ]
        lookup = {1: 'For God so loved the world', 2: 'For God did not send his Son'}

        plain, display = views._join_passage_text(verses, lookup)

        self.assertEqual(
            plain,
            'For God so loved the world For God did not send his Son',
        )
        self.assertEqual(
            display,
            '<span class="sup">16</span> For God so loved the world '
            '<span class="sup">17</span> For God did not send his Son',
        )

    def test_strip_superscripts_removes_unicode_markers(self):
        text = '¹⁶ For God so loved the world ⁴²'

        self.assertEqual(views._strip_superscripts(text), ' For God so loved the world ')

    def test_strip_superscripts_removes_sup_span_markup(self):
        text = '<span class="sup">16</span> For God so loved the world <span class="sup">17</span>'

        self.assertEqual(views._strip_superscripts(text), ' For God so loved the world ')


class RelatedSermonSerializationTests(unittest.TestCase):
    def make_passage(self, pk, start, end=None, *, ref_text='', context_note='', preached_on=None, speaker='Speaker'):
        sermon = SimpleNamespace(
            pk=pk,
            preached_on=preached_on or date(2024, 1, pk),
            title=f'Sermon {pk}',
            speaker_name=speaker,
        )

        end_value = end if end is not None else start

        class Passage(SimpleNamespace):
            def ref_display(self_inner):
                return self_inner._display

        return Passage(
            sermon=sermon,
            start_id=start,
            end_id=end_value,
            ref_text=ref_text,
            context_note=context_note,
            start_verse=SimpleNamespace(verse_id=start),
            end_verse=SimpleNamespace(verse_id=end_value),
            end_verse_id=end,
            _display=ref_text or f'Passage {pk}',
        )

    def test_single_verse_prioritizes_exact_matches(self):
        passages = [
            self.make_passage(1, 99, 101, ref_text='John 3:15–17'),
            self.make_passage(2, 100, 100, ref_text='John 3:16'),
            self.make_passage(3, 97, 104, ref_text='John 3:13–18'),
        ]

        serialized = views._serialize_related_passages({'from_ref': 'John 3:16'}, 100, 100, passages)

        self.assertEqual([item['ref_text'] for item in serialized], ['John 3:16', 'John 3:15–17', 'John 3:13–18'])
        self.assertTrue(serialized[0]['detail_url'].endswith('from_ref=John+3%3A16'))

    def test_passage_results_rank_by_overlap_then_length(self):
        passages = [
            self.make_passage(1, 100, 102, ref_text='John 3:16–18'),
            self.make_passage(2, 99, 103, ref_text='John 3:15–19'),
            self.make_passage(3, 100, 101, ref_text='John 3:16–17'),
            self.make_passage(4, 100, 110, ref_text='John 3:16–4:2'),
        ]

        serialized = views._serialize_related_passages({'from_ref': 'John 3:16-18'}, 100, 102, passages)

        self.assertEqual(
            [item['ref_text'] for item in serialized],
            ['John 3:16–18', 'John 3:15–19', 'John 3:16–17', 'John 3:16–4:2'],
        )
