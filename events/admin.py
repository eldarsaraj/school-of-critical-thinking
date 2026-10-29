import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import EventSession, EventRegistration


@admin.register(EventSession)
class EventSessionAdmin(admin.ModelAdmin):
    list_display = ["title", "date_time", "zoom_link", "is_active", "registration_count"]

    def registration_count(self, obj):
        return obj.registrations.count()

    registration_count.short_description = "Registrations"


def export_registrations_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=event_registrations.csv"
    writer = csv.writer(response)
    writer.writerow(["Name", "Email", "Session", "School", "Question", "Newsletter", "Source", "Created"])
    for r in queryset.select_related("session"):
        writer.writerow([
            r.name, r.email, str(r.session), r.school,
            r.question, r.opt_in_newsletter, r.source, r.created_at,
        ])
    return response


export_registrations_csv.short_description = "Export selected registrations as CSV"


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "session", "school", "opt_in_newsletter", "source", "created_at"]
    list_filter = ["session", "school", "source", "opt_in_newsletter"]
    search_fields = ["name", "email", "school"]
    actions = [export_registrations_csv]
