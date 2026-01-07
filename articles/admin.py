from django.contrib import admin
from django.utils.safestring import mark_safe
import markdown

from .models import Article, ArticleImage


class ArticleImageInline(admin.TabularInline):
    model = ArticleImage
    extra = 1
    fields = ("image", "title", "alt_text", "image_url_preview")
    readonly_fields = ("image_url_preview",)

    def image_url_preview(self, obj):
        if not obj or not getattr(obj, "image", None):
            return "—"
        url = obj.image.url
        return mark_safe(
            f"<div style='display:flex; gap:12px; align-items:center;'>"
            f"<img src='{url}' style='height:50px; width:auto; border-radius:6px; border:1px solid #ddd;' />"
            f"<a href='{url}' target='_blank' rel='noopener'>Open</a>"
            f"<code style='user-select:all; padding:2px 6px; border:1px solid #eee; border-radius:4px;'>{url}</code>"
            f"</div>"
        )

    image_url_preview.short_description = "URL"


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "published_at")
    list_filter = ("status", "author")
    search_fields = ("title", "author", "slug", "content_markdown")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("preview_html",)
    filter_horizontal = ("related",)
    inlines = [ArticleImageInline]

    fieldsets = (
        (None, {"fields": ("title", "slug", "author", "status", "published_at")}),
        (
            "Index summary (required for published articles)",
            {"fields": ("summary", "cover_image")},
        ),
        ("Related reading", {"fields": ("related",)}),
        (
            "Article content (Markdown)",
            {"fields": ("content_markdown", "preview_html")},
        ),
    )

    def preview_html(self, obj):
        if not obj or not obj.content_markdown:
            return "—"
        html = markdown.markdown(obj.content_markdown, extensions=["extra"])
        return mark_safe(f"<div style='max-width: 760px'>{html}</div>")

    preview_html.short_description = "Preview"


@admin.register(ArticleImage)
class ArticleImageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "article", "created_at")
    list_filter = ("article",)
    search_fields = ("title", "alt_text", "image")
