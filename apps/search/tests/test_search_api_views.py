from types import SimpleNamespace
from unittest import mock

from rest_framework.test import APIRequestFactory, force_authenticate

from apps.search import api_views


factory = APIRequestFactory()


def _auth_get(path: str):
    request = factory.get(path)
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
    return request


def test_search_view_filters_when_query_present():
    sermon = SimpleNamespace(sermon_id=1)
    filter_qs = mock.Mock()
    filter_qs.order_by.return_value = [sermon]

    manager = mock.Mock()
    manager.none.return_value = []
    manager.filter.return_value = filter_qs

    serializer = mock.Mock()
    serializer.data = [{"sermon_id": 1}]

    request = _auth_get("/api/search?q=grace")
    with mock.patch.object(api_views.Sermon, "objects", manager), \
         mock.patch.object(api_views, "SermonSerializer", return_value=serializer) as serializer_cls:
        response = api_views.SermonSearchView.as_view()(request)

    manager.filter.assert_called_once_with(title__icontains="grace")
    filter_qs.order_by.assert_called_once_with("-preached_on")
    serializer_cls.assert_called_once_with([sermon], many=True)
    assert response.status_code == 200
    assert response.data == {"sermons": [{"sermon_id": 1}]}


def test_search_view_returns_empty_payload_without_query():
    manager = mock.Mock()
    manager.none.return_value = []

    serializer = mock.Mock()
    serializer.data = []

    request = _auth_get("/api/search")
    with mock.patch.object(api_views.Sermon, "objects", manager), \
         mock.patch.object(api_views, "SermonSerializer", return_value=serializer):
        response = api_views.SermonSearchView.as_view()(request)

    manager.none.assert_called_once()
    assert response.status_code == 200
    assert response.data == {"sermons": []}


def test_reference_search_rejects_missing_query():
    response = api_views.ReferenceSearchView.as_view()(_auth_get("/api/search/reference"))

    assert response.status_code == 400
    assert response.data["detail"] == "Provide a reference in the 'q' query param."


def test_reference_search_serializes_parsed_reference():
    start = SimpleNamespace()
    end = SimpleNamespace()

    serializer = mock.Mock()
    serializer.data = {"verse_id": 1}

    request = _auth_get("/api/search/reference?q=John+3%3A16")
    with mock.patch.object(api_views, "tolerant_parse_reference", return_value=(start, end)), \
         mock.patch.object(api_views, "BibleVerseSerializer", return_value=serializer):
        response = api_views.ReferenceSearchView.as_view()(request)

    assert response.status_code == 200
    assert response.data == {
        "reference": mock.ANY,
        "start": {"verse_id": 1},
        "end": {"verse_id": 1},
    }


class DummyQuerySet(list):
    def __init__(self, items):
        super().__init__(items)
        self.filters = []
        self.annotations = {}
        self.ordering = ()

    def filter(self, *args, **kwargs):
        if args:
            self.filters.extend(args)
        if kwargs:
            self.filters.append(kwargs)
        return self

    def annotate(self, **kwargs):
        self.annotations.update(kwargs)
        return self

    def order_by(self, *args):
        self.ordering = args
        return self

    def count(self):
        return len(self)

    def __getitem__(self, item):
        return list(self)[item]


class DummyManager:
    def __init__(self, items):
        self.items = items
        self.selected_related = ()

    def select_related(self, *args):
        self.selected_related = args
        return DummyQuerySet(self.items)


def test_verse_search_requires_query():
    response = api_views.VerseSearchView.as_view()(_auth_get("/api/search"))

    assert response.status_code == 400
    assert response.data["detail"] == "Provide a search query in the 'q' query param."


def test_verse_search_returns_ranked_results():
    book = SimpleNamespace(name="John", order_num=43, testament="NT")
    verse = SimpleNamespace(book=book, chapter=3, verse=16, verse_id=31601)
    verse_text = SimpleNamespace(verse=verse, translation="ESV", plain_text="For God so loved the world")
    manager = DummyManager([verse_text])

    request = _auth_get("/api/search?q=for+God+so+loved&page=1")
    with mock.patch.object(api_views.VerseText, "objects", manager):
        response = api_views.VerseSearchView.as_view()(request)

    assert manager.selected_related == ("verse__book", "verse")
    assert response.status_code == 200
    assert response.data["type"] == "text_results"
    assert response.data["query"] == "for God so loved"
    assert response.data["total"] == 1
    assert response.data["results"][0] == {
        "order_num": 1,
        "verse_id": 31601,
        "reference": "John 3:16",
        "book": "John",
        "chapter": 3,
        "verse": 16,
        "translation": "ESV",
        "text": "For God so loved the world",
    }


def test_flexible_search_skips_substring_only_matches():
    book = SimpleNamespace(name="Psalms", order_num=19, testament="OT")
    verse = SimpleNamespace(book=book, chapter=24, verse=4, verse_id=24004)
    verse_text = SimpleNamespace(verse=verse, translation="ESV", plain_text="He who has clean hands and a pure heart")
    verse_text_substring = SimpleNamespace(
        verse=verse, translation="NIV", plain_text="Do not count me among the unclean or wicked"
    )
    manager = DummyManager([verse_text_substring, verse_text])

    request = _auth_get("/api/search?q=clean&page=1")
    with mock.patch.object(api_views.VerseText, "objects", manager):
        response = api_views.VerseSearchView.as_view()(request)

    assert response.status_code == 200
    assert response.data["total"] == 1
    assert response.data["results"][0]["text"] == "He who has clean hands and a pure heart"


def test_flexible_search_ranks_by_term_coverage_and_proximity():
    book = SimpleNamespace(name="John", order_num=43, testament="NT")
    verse_a = SimpleNamespace(book=book, chapter=13, verse=34, verse_id=1334)
    verse_b = SimpleNamespace(book=book, chapter=14, verse=15, verse_id=1415)
    tight_match = SimpleNamespace(
        verse=verse_a,
        translation="ESV",
        plain_text="love one another just as I have loved you",
    )
    sparse_match = SimpleNamespace(
        verse=verse_b,
        translation="ESV",
        plain_text="If you love me, keep my commandments and love is shown by obedience",
    )
    manager = DummyManager([sparse_match, tight_match])

    request = _auth_get("/api/search?q=love+one+another")
    with mock.patch.object(api_views.VerseText, "objects", manager):
        response = api_views.VerseSearchView.as_view()(request)

    assert response.status_code == 200
    assert response.data["results"][0]["text"] == "love one another just as I have loved you"
