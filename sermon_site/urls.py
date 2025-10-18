from django.contrib import admin
from django.urls import path, include
from archive.api_verse import api as archive_api
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('archive.urls')),
    path('api/', archive_api.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

