from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from .ics import generate_ics


def send_confirmation_email(registration):
    """Send confirmation email with .ics attachment after registration."""
    session = registration.session
    subject = f"You're registered: Hunter Test Briefing — {session.date_time.strftime('%b %d')}"
    html = render_to_string("events/email_confirmation.html", {
        "registration": registration,
        "session": session,
    })
    email = EmailMessage(
        subject=subject,
        body=html,
        to=[registration.email],
    )
    email.content_subtype = "html"

    ics_content = generate_ics(session)
    email.attach("briefing.ics", ics_content, "text/calendar")

    email.send(fail_silently=True)


def send_reminder_email(registration, hours_label):
    """Send a reminder email with the Zoom link."""
    session = registration.session
    if hours_label == "24h":
        subject = f"Tomorrow: Hunter Test Briefing — {session.date_time.strftime('%b %d')}"
    else:
        subject = "Starting soon: Hunter Test Briefing in 1 hour"

    html = render_to_string("events/email_reminder.html", {
        "registration": registration,
        "session": session,
        "hours_label": hours_label,
    })
    email = EmailMessage(
        subject=subject,
        body=html,
        to=[registration.email],
    )
    email.content_subtype = "html"
    email.send(fail_silently=True)
