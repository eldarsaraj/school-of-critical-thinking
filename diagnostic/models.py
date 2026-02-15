from __future__ import annotations

from django.db import models


class DiagnosticLead(models.Model):
    email = models.EmailField()
    full_name = models.CharField(max_length=200, blank=True, default="")
    organization = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    # store module IDs as a simple comma-separated string for v1
    module_ids = models.TextField(blank=True, default="")

    # optional: store full breakpoint result later
    version = models.CharField(max_length=20, default="v0_1")

    def __str__(self) -> str:
        return self.email
