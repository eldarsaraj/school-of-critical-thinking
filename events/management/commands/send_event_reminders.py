from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import EventRegistration
from events.emails import send_reminder_email


class Command(BaseCommand):
    help = "Send 24h and 1h reminder emails for upcoming event sessions."

    def handle(self, *args, **options):
        now = timezone.now()

        # 24-hour reminders (window: 23.9h to 24.1h from now)
        window_24_start = now + timezone.timedelta(hours=23.9)
        window_24_end = now + timezone.timedelta(hours=24.1)
        pending_24 = EventRegistration.objects.filter(
            reminder_24h_sent=False,
            session__date_time__gte=window_24_start,
            session__date_time__lte=window_24_end,
        ).select_related("session")

        count_24 = 0
        for reg in pending_24:
            send_reminder_email(reg, "24h")
            reg.reminder_24h_sent = True
            reg.save(update_fields=["reminder_24h_sent"])
            count_24 += 1

        # 1-hour reminders (window: 0.9h to 1.1h from now)
        window_1_start = now + timezone.timedelta(hours=0.9)
        window_1_end = now + timezone.timedelta(hours=1.1)
        pending_1 = EventRegistration.objects.filter(
            reminder_1h_sent=False,
            session__date_time__gte=window_1_start,
            session__date_time__lte=window_1_end,
        ).select_related("session")

        count_1 = 0
        for reg in pending_1:
            send_reminder_email(reg, "1h")
            reg.reminder_1h_sent = True
            reg.save(update_fields=["reminder_1h_sent"])
            count_1 += 1

        self.stdout.write(f"Sent {count_24} 24h reminders, {count_1} 1h reminders.")
