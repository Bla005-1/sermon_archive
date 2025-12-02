from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("sermons/", include("apps.sermons.urls")),
    path("attachments/", include("apps.attachments.urls")),
    path("bible/", include("apps.bible.urls")),
    path("widget/", include("apps.widget.urls")),
    path("search/", include("apps.search.urls")),
]
