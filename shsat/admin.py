import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import Parent, Test, Question, TestAttempt, Answer, ManualScore, CutoffScore


def export_emails_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="shsat_parents.csv"'
    writer = csv.writer(response)
    writer.writerow(["email", "child_nickname", "child_grade", "has_paid", "joined"])
    for parent in queryset.select_related("user"):
        writer.writerow([
            parent.user.email,
            parent.child_nickname or "",
            parent.child_grade or "",
            parent.has_paid,
            parent.created_at.strftime("%Y-%m-%d"),
        ])
    return response

export_emails_csv.short_description = "Export selected parents as CSV"


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ["get_email", "child_nickname", "child_grade", "has_paid", "created_at"]
    search_fields = ["user__email", "user__first_name", "child_nickname"]
    list_filter = ["has_paid", "child_grade"]
    actions = [export_emails_csv]

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"
    get_email.admin_order_field = "user__email"


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ["section", "question_number", "question_type", "topic", "difficulty", "correct_answer"]
    ordering = ["section", "question_number"]


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ["title", "source", "is_free", "is_published", "order", "total_questions"]
    list_filter = ["is_free", "is_published"]
    inlines = [QuestionInline]

    def total_questions(self, obj):
        return obj.questions.count()
    total_questions.short_description = "Questions"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["test", "section", "question_number", "question_type", "topic", "difficulty", "correct_answer"]
    list_filter = ["test", "section", "difficulty", "question_type"]
    search_fields = ["question_text", "topic"]


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ["question", "selected_answer", "is_correct", "is_flagged"]
    readonly_fields = ["is_correct"]


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ["parent", "test", "started_at", "is_completed", "composite_score"]
    list_filter = ["is_completed", "test"]
    readonly_fields = ["started_at", "submitted_at"]
    inlines = [AnswerInline]


@admin.register(ManualScore)
class ManualScoreAdmin(admin.ModelAdmin):
    list_display = ["parent", "source_name", "date", "ela_correct", "math_correct"]
    list_filter = ["source_name"]
    search_fields = ["parent__user__email", "source_name"]


@admin.register(CutoffScore)
class CutoffScoreAdmin(admin.ModelAdmin):
    list_display = ["school_short", "school_name", "admissions_year", "cutoff_score", "approximate_seats"]
    list_filter = ["admissions_year"]
