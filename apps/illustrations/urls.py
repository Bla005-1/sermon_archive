from django.urls import path

from .api_views import IllustrationDetailView, IllustrationListCreateView

urlpatterns = [
    path("", IllustrationListCreateView.as_view(), name="illustration-list"),
    path("<int:pk>/", IllustrationDetailView.as_view(), name="illustration-detail"),
]
