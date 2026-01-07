from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
import re


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)

    author = models.CharField(max_length=120)

    # Optional cover image for listings + social sharing
    cover_image = models.ImageField(
        upload_to="articles/covers/",
        blank=True,
        null=True,
    )

    # Short editorial summary for index / previews
    summary = models.CharField(max_length=280, blank=True)

    # CMS-friendly: write in Markdown, render later
    content_markdown = models.TextField(blank=True)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    related = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="related_to",
    )

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        """
        Enforce meaning:
        - A published article must have a non-empty summary and a publication date.
        - Summary must read as 1–2 complete sentences (no mid-sentence cutoffs).
        """
        super().clean()

        if self.status != self.Status.PUBLISHED:
            return

        s = (self.summary or "").strip()

        if not s:
            raise ValidationError(
                {"summary": "Summary is required for published articles."}
            )

        # Must end like a completed thought.
        # Accepts ., !, ?, or … (unicode ellipsis).
        if not re.search(r"[.!?\u2026]$", s):
            raise ValidationError(
                {"summary": "Summary must end with punctuation (., !, ?, or …)."}
            )

        # Keep it editorially tight: 1–2 sentences.
        endings = re.findall(r"[.!?\u2026]", s)
        if len(endings) > 2:
            raise ValidationError({"summary": "Keep the summary to 1–2 sentences."})

        if not self.published_at:
            self.published_at = timezone.now()

    def publish(self):
        self.status = self.Status.PUBLISHED
        if not self.published_at:
            self.published_at = timezone.now()
        self.full_clean()  # enforce rules
        self.save()

    from django.urls import reverse

    def get_absolute_url(self):
        return reverse("articles_detail", args=[self.slug])


class ArticleImage(models.Model):
    # Optional: link to an article (so you can keep images organized)
    article = models.ForeignKey(
        "Article",
        on_delete=models.CASCADE,
        related_name="images",
        blank=True,
        null=True,
    )

    # This will upload to Cloudinary because your DEFAULT file storage is Cloudinary
    image = models.ImageField(upload_to="articles/inline/")

    title = models.CharField(max_length=200, blank=True)  # admin-only label
    alt_text = models.CharField(max_length=300, blank=True)  # for accessibility/SEO
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.title:
            return self.title
        return self.image.name
