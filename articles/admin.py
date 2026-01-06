from django.contrib import admin
from django.utils.safestring import mark_safe
import markdown

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "published_at")
    list_filter = ("status", "author")
    search_fields = ("title", "author", "slug", "content_markdown")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("preview_html",)
    filter_horizontal = ("related",)

    fieldsets = (
        (None, {"fields": ("title", "slug", "author", "status", "published_at")}),
        (
            "Index summary (required for published articles)",
            {
                "fields": ("summary", "cover_image"),  # <-- added
            },
        ),
        (
            "Related reading",
            {
                "fields": ("related",),
            },
        ),
        (
            "Article content (Markdown)",
            {
                "fields": ("content_markdown", "preview_html"),
            },
        ),
    )

    def preview_html(self, obj):
        if not obj or not obj.content_markdown:
            return "—"
        html = markdown.markdown(obj.content_markdown, extensions=["extra"])
        return mark_safe(f"<div style='max-width: 760px'>{html}</div>")

    preview_html.short_description = "Preview"
