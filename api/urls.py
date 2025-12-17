from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("sermons/", include("apps.sermons.urls")),
    path("attachments/", include("apps.attachments.urls")),
    path("verses/sermons/", include("apps.sermons.verse_urls")),
    path("verses/", include("apps.bible.urls")),
    path("widget/", include("apps.widget.urls")),
    path("search/", include("apps.search.urls")),
]
