import uuid

from django.db import models


class DiagnosticLead(models.Model):
    email = models.EmailField(unique=True)

    full_name = models.CharField(max_length=200, blank=True, default="")
    organization = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    module_ids = models.TextField(blank=True, default="")
    version = models.CharField(max_length=20, default="v0_1")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self) -> str:
        return self.email
