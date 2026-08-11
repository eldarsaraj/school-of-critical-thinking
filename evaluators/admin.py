from django.contrib import admin

from .models import EssayEvaluation


@admin.register(EssayEvaluation)
class EssayEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        "get_parent_email", "get_test", "evaluated_at",
        "get_word_count", "get_on_prompt", "succeeded",
    ]
    list_filter = ["answer__attempt__test", "answer__attempt__test__exam_type"]
    search_fields = ["answer__attempt__parent__user__email"]
    readonly_fields = [
        "answer", "evaluated_at", "evaluation_data", "feedback", "error",
    ]
    ordering = ["-evaluated_at"]

    def get_parent_email(self, obj):
        try:
            return obj.answer.attempt.parent.user.email
        except Exception:
            return "—"
    get_parent_email.short_description = "Parent"

    def get_test(self, obj):
        try:
            return obj.answer.attempt.test.title
        except Exception:
            return "—"
    get_test.short_description = "Test"

    def get_word_count(self, obj):
        return obj.evaluation_data.get("word_count", "—") if obj.evaluation_data else "—"
    get_word_count.short_description = "Words"

    def get_on_prompt(self, obj):
        v = obj.evaluation_data.get("on_prompt_relevance") if obj.evaluation_data else None
        return f"{round(v * 100)}%" if v is not None else "—"
    get_on_prompt.short_description = "On-prompt"
