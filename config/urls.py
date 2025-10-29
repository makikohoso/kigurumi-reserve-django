from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("reservations.urls")),
    path('favicon.ico', RedirectView.as_view(url='/static/admin/img/favicon.png', permanent=True)),
]

# Media files serving (本番環境でも提供)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Development environment static file serving
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
