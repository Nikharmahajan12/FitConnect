
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("admin/", admin.site.urls),

    # Client and trainer logout
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(
            next_page="core:website_home"
        ),
        name="client_logout",
    ),

    # Core application URLs
    path("", include("core.urls")),

    # Accounts application URLs
    path("", include("accounts.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
