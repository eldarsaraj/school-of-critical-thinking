import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import (
    Parent, SHSATParent, HunterParent,
    Test, TestAttempt, Answer,
    QuestionReport,
    Tutor, TutorStudent,
)


# ---------------------------------------------------------------------------
# CSV export actions
# ---------------------------------------------------------------------------

def _export_parents_csv(queryset, filename):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
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


def export_shsat_parents_csv(modeladmin, request, queryset):
    return _export_parents_csv(queryset, "shsat_parents.csv")
export_shsat_parents_csv.short_description = "Export selected as CSV"


def export_hunter_parents_csv(modeladmin, request, queryset):
    return _export_parents_csv(queryset, "hunter_parents.csv")
export_hunter_parents_csv.short_description = "Export selected as CSV"


# ---------------------------------------------------------------------------
# Shared parent admin base
# ---------------------------------------------------------------------------

class _BaseParentAdmin(admin.ModelAdmin):
    list_display = ["get_email", "child_nickname", "child_grade", "has_paid", "created_at"]
    search_fields = ["user__email", "user__first_name", "child_nickname"]
    list_filter = ["has_paid", "child_grade"]
    ordering = ["-created_at"]

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"
    get_email.admin_order_field = "user__email"


# ---------------------------------------------------------------------------
# SHSAT Parents (platform = 'shsat')
# ---------------------------------------------------------------------------

@admin.register(SHSATParent)
class SHSATParentAdmin(_BaseParentAdmin):
    actions = [export_shsat_parents_csv]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(platform="shsat")


# ---------------------------------------------------------------------------
# Hunter Parents (platform = 'hunter')
# ---------------------------------------------------------------------------

@admin.register(HunterParent)
class HunterParentAdmin(_BaseParentAdmin):
    actions = [export_hunter_parents_csv]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(platform="hunter")


# ---------------------------------------------------------------------------
# Tests — read-only overview
# ---------------------------------------------------------------------------

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ["title", "exam_type", "source", "is_free", "is_drill", "is_published", "order", "total_questions"]
    list_filter = ["exam_type", "is_free", "is_drill", "is_published"]

    def total_questions(self, obj):
        return obj.questions.count()
    total_questions.short_description = "Questions"


# ---------------------------------------------------------------------------
# Test Attempts
# ---------------------------------------------------------------------------

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ["question", "selected_answer", "is_correct", "is_flagged"]
    readonly_fields = ["is_correct"]


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ["get_parent_email", "get_exam_type", "test", "is_completed", "composite_score", "submitted_at"]
    list_filter = ["test__exam_type", "is_completed", "test"]
    search_fields = ["parent__user__email", "parent__child_nickname"]
    readonly_fields = ["started_at", "submitted_at"]
    ordering = ["-submitted_at"]
    inlines = [AnswerInline]

    def get_parent_email(self, obj):
        return obj.parent.user.email
    get_parent_email.short_description = "Parent"
    get_parent_email.admin_order_field = "parent__user__email"

    def get_exam_type(self, obj):
        return obj.test.exam_type.upper()
    get_exam_type.short_description = "Platform"
    get_exam_type.admin_order_field = "test__exam_type"


# ---------------------------------------------------------------------------
# Question Reports
# ---------------------------------------------------------------------------

@admin.register(QuestionReport)
class QuestionReportAdmin(admin.ModelAdmin):
    list_display = ["short_question", "get_exam_type", "get_test", "get_parent_email", "reason_preview", "created_at", "resolved"]
    list_filter = ["resolved", "question__test__exam_type", "question__test"]
    list_editable = ["resolved"]
    search_fields = ["question__question_text", "reason", "parent__user__email"]
    readonly_fields = ["question", "attempt", "parent", "reason", "created_at"]
    ordering = ["-created_at"]

    def short_question(self, obj):
        return str(obj.question)
    short_question.short_description = "Question"

    def get_exam_type(self, obj):
        return obj.question.test.exam_type.upper()
    get_exam_type.short_description = "Platform"

    def get_test(self, obj):
        return obj.question.test.title
    get_test.short_description = "Test"
    get_test.admin_order_field = "question__test"

    def get_parent_email(self, obj):
        return obj.parent.user.email if obj.parent else "—"
    get_parent_email.short_description = "Parent"

    def reason_preview(self, obj):
        return obj.reason[:80] if obj.reason else "—"
    reason_preview.short_description = "Reason"


# ---------------------------------------------------------------------------
# Tutors
# ---------------------------------------------------------------------------

class TutorStudentInline(admin.TabularInline):
    model = TutorStudent
    extra = 0
    fields = ["parent", "nickname", "added_at"]
    readonly_fields = ["added_at"]


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ["get_email", "business_name", "invite_code", "subscription_status", "student_limit", "student_count", "created_at"]
    list_filter = ["subscription_status"]
    search_fields = ["user__email", "user__first_name", "business_name", "invite_code"]
    readonly_fields = ["invite_code", "created_at"]
    ordering = ["-created_at"]
    inlines = [TutorStudentInline]

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"
    get_email.admin_order_field = "user__email"

    def student_count(self, obj):
        return obj.students.count()
    student_count.short_description = "Linked"


@admin.register(TutorStudent)
class TutorStudentAdmin(admin.ModelAdmin):
    list_display = ["get_tutor_email", "get_parent_email", "nickname", "added_at"]
    search_fields = ["tutor__user__email", "parent__user__email", "nickname"]
    ordering = ["-added_at"]

    def get_tutor_email(self, obj):
        return obj.tutor.user.email
    get_tutor_email.short_description = "Tutor"

    def get_parent_email(self, obj):
        return obj.parent.user.email
    get_parent_email.short_description = "Student"
