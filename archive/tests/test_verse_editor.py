import os
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

    def test_join_passage_text_includes_superscript_markers(self):
        verses = [
            SimpleNamespace(verse_id=1, verse=16),
            SimpleNamespace(verse_id=2, verse=17),
        ]
        lookup = {1: 'For God so loved the world', 2: 'For God did not send his Son'}

        joined = views._join_passage_text(verses, lookup)

        self.assertEqual(
            joined,
            '¹⁶ For God so loved the world ¹⁷ For God did not send his Son',
        )
