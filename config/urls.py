"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include, re_path

admin.site.site_header = "School of Critical Thinking"
admin.site.site_title = "Admin"
admin.site.index_title = "Dashboard"

# Force admin app ordering: priority apps first, low-priority last
_ADMIN_APP_ORDER = [
    "shsat",          # Test Prep — parents, tutors, attempts
    "evaluators",     # Essay Evaluations
    "pages",          # Leads & Messages
    "articles",       # Research articles
    "auth",           # Authentication
    "diagnostic",     # Diagnostic (legacy)
    "axis5",          # AXIS-5 (low priority)
]

_original_get_app_list = admin.AdminSite.get_app_list

def _ordered_get_app_list(self, request, app_label=None):
    app_list = _original_get_app_list(self, request, app_label=app_label)
    order_map = {label: i for i, label in enumerate(_ADMIN_APP_ORDER)}
    app_list.sort(key=lambda a: order_map.get(a["app_label"], 999))
    return app_list

admin.AdminSite.get_app_list = _ordered_get_app_list
from django.conf import settings
from django.views.static import serve
from django.contrib.sitemaps.views import sitemap
from articles.sitemaps import ArticleSitemap
from pages.sitemaps import StaticSitemap
from django.views.generic import RedirectView

sitemaps = {
    "articles": ArticleSitemap,
    "pages": StaticSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("articles/", include("articles.urls")),
    path("", include("pages.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("diagnostic/", include("diagnostic.urls")),
    path("shsat/", include("shsat.urls")),
    path("hunter/", include("shsat.hunter_urls")),
    path("tutor/", include("shsat.tutor_urls")),
    path("axis5/", include("axis5.urls")),
    path(
        "python-detective/",
        RedirectView.as_view(
            url="/static/python-detective/index.html", permanent=False
        ),
    ),
]

# Serve uploaded media files (works even when DEBUG=False)
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
