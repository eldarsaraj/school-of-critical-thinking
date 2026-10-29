from django.shortcuts import render, redirect
from django.db import IntegrityError

from .models import EventSession, EventRegistration
from .emails import send_confirmation_email

# Known source codes → school name pre-fill
SOURCE_SCHOOL_MAP = {
    # Add mappings as needed, e.g.:
    # "w1-21k098": "PS 21",
}


def hunter_briefing(request):
    src = request.GET.get("src", "")

    if request.GET.get("registered"):
        return render(request, "events/hunter_briefing.html", {"registered": True})

    sessions = EventSession.objects.filter(is_active=True)

    if request.method == "POST":
        # Honeypot check
        if request.POST.get("website"):
            return redirect("hunter_briefing")

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        session_id = request.POST.get("session", "").strip()
        school = request.POST.get("school", "").strip()
        question = request.POST.get("question", "").strip()
        opt_in = request.POST.get("opt_in_newsletter") == "on"
        source = request.POST.get("source", "").strip()

        errors = {}
        if not name:
            errors["name"] = "Name is required."
        if not email:
            errors["email"] = "Email is required."
        if not session_id:
            errors["session"] = "Please choose a session."

        session_obj = None
        if session_id:
            try:
                session_obj = EventSession.objects.get(id=session_id, is_active=True)
            except EventSession.DoesNotExist:
                errors["session"] = "Invalid session selected."

        if errors:
            return render(request, "events/hunter_briefing.html", {
                "sessions": sessions,
                "errors": errors,
                "form": {
                    "name": name, "email": email, "session": session_id,
                    "school": school, "question": question,
                    "opt_in_newsletter": opt_in, "source": source,
                },
                "src": src,
            })

        try:
            registration = EventRegistration.objects.create(
                name=name,
                email=email,
                session=session_obj,
                school=school,
                question=question,
                opt_in_newsletter=opt_in,
                source=source,
            )
        except IntegrityError:
            errors["email"] = "You're already registered for this session."
            return render(request, "events/hunter_briefing.html", {
                "sessions": sessions,
                "errors": errors,
                "form": {
                    "name": name, "email": email, "session": session_id,
                    "school": school, "question": question,
                    "opt_in_newsletter": opt_in, "source": source,
                },
                "src": src,
            })

        send_confirmation_email(registration)
        return redirect(f"/hunter-briefing/?registered=1")

    # GET
    prefill_school = SOURCE_SCHOOL_MAP.get(src, "")
    return render(request, "events/hunter_briefing.html", {
        "sessions": sessions,
        "src": src,
        "form": {"source": src, "school": prefill_school},
    })
