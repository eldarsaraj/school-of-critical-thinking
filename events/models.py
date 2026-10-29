import uuid

from django.db import models


class EventSession(models.Model):
    title = models.CharField(max_length=200)
    date_time = models.DateTimeField()
    zoom_link = models.URLField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["date_time"]

    def __str__(self):
        return f"{self.title} — {self.date_time.strftime('%b %d, %Y %I:%M %p')}"


class EventRegistration(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    session = models.ForeignKey(
        EventSession, on_delete=models.CASCADE, related_name="registrations"
    )
    school = models.CharField(max_length=200, blank=True)
    question = models.TextField(blank=True)
    opt_in_newsletter = models.BooleanField(default=False)
    source = models.CharField(max_length=100, blank=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("email", "session")]

    def __str__(self):
        return f"{self.name} — {self.session}"
