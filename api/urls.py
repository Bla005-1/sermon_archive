from django.urls import include, path

urlpatterns = [
    path("", include("apps.sermons.urls")),
]
