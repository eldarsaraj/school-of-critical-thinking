"""
Django model for persisting essay evaluation results.
"""
from django.db import models


class EssayEvaluation(models.Model):
    """Stores the result of an AI essay evaluation for one Answer (essay question)."""
    answer = models.OneToOneField(
        "shsat.Answer",
        on_delete=models.CASCADE,
        related_name="evaluation",
    )
    evaluated_at = models.DateTimeField(auto_now_add=True)
    # Full EssayEvaluation Pydantic model serialized as JSON
    evaluation_data = models.JSONField(default=dict)
    # Quick-access feedback text (extracted from evaluation_data)
    feedback = models.TextField(blank=True, default="")
    # Set if the LLM call failed
    error = models.TextField(blank=True, default="")

    def __str__(self):
        return f"EssayEvaluation for Answer {self.answer_id}"

    @property
    def succeeded(self):
        return bool(self.evaluation_data) and not self.error
