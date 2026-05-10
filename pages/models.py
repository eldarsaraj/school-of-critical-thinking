from django.db import models


class CurriculumLead(models.Model):
    email = models.EmailField()
    source = models.CharField(max_length=60, default="module-1-sample")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} ({self.source})"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Newsletter subscriber"
        verbose_name_plural = "Newsletter subscribers"

    def __str__(self):
        return self.email


class ModuleWaitlist(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Module waitlist signup"
        verbose_name_plural = "Module waitlist signups"

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField()

    # Optional context (from querystring)
    path = models.CharField(max_length=20, blank=True)  # "adult" / "parent" / ""
    source = models.CharField(max_length=40, blank=True)  # e.g. "start" / ""

    # Timestamp
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.name} ({self.email})"
