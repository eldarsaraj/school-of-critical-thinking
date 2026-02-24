"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include, re_path
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
