from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import RedirectView


def health_check(request):
    """Simple health check endpoint for Fly.io."""
    return HttpResponse("OK")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("tutor/", include("apps.tutor.urls")),
    path("writing/", include("apps.writing.urls")),
    path("signing/", include("apps.signing.urls")),
    path("health-check/", health_check, name="health_check"),
    # Redirect the root URL to the dashboard
    path("", RedirectView.as_view(pattern_name="dashboard:home", permanent=False)),
]

# Add debug toolbar URLs in development
if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns += [
            path("__debug__/", include(debug_toolbar.urls)),
        ]
    except ModuleNotFoundError:
        pass  # Skip debug toolbar if not installed

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
