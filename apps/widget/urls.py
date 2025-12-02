from rest_framework.routers import DefaultRouter

from .api_views import BibleWidgetViewSet

router = DefaultRouter()
router.register("", BibleWidgetViewSet, basename="widget")

urlpatterns = router.urls
