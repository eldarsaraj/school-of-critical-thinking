from django.shortcuts import render, redirect
from django.http import Http404, FileResponse, HttpResponse
from django.utils import timezone
from django.template import loader
from django.conf import settings


from .book_data import BOOKS
from .models import ContactMessage, CurriculumLead, ModuleWaitlist, NewsletterSubscriber
from .module_data import MODULES_BY_SLUG


def home(request):
    return render(request, "pages/home.html")


def test_prep(request):
    return render(request, "pages/test_prep.html")


def about(request):
    return render(request, "pages/about.html")


def books(request):
    return redirect("home")


def book_detail(request, slug):
    return redirect("home")


def families(request):
    waitlisted = request.GET.get("waitlisted") == "1"
    return render(request, "pages/families.html", {"waitlisted": waitlisted})


def organizations(request):
    sent = request.GET.get("sent") == "1"
    if request.method == "POST":
        if request.POST.get("website"):
            return redirect("/organizations/?sent=1")

        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        message = (request.POST.get("message") or "").strip()
        errors = {}
        if not name:
            errors["name"] = "Name is required."
        if not email:
            errors["email"] = "Email is required."
        if not message:
            errors["message"] = "Message is required."
        if not errors:
            ContactMessage.objects.create(name=name, email=email, message=message)
            return redirect("/organizations/?sent=1")
        return render(request, "pages/organizations.html", {
            "errors": errors,
            "form": {"name": name, "email": email, "message": message},
        })
    return render(request, "pages/organizations.html", {"sent": sent})


def newsletter_signup(request):
    if request.method != "POST":
        return redirect("home")
    if request.POST.get("website"):
        referer = request.META.get("HTTP_REFERER", "/")
        return redirect(referer)
    email = (request.POST.get("email") or "").strip()
    if email:
        NewsletterSubscriber.objects.get_or_create(email=email)
    referer = request.META.get("HTTP_REFERER", "/")
    return redirect(referer)


def waitlist_signup(request):
    if request.method != "POST":
        return redirect("curriculum")
    if request.POST.get("website"):
        return redirect("/curriculum/?waitlisted=1")
    email = (request.POST.get("email") or "").strip()
    if email:
        ModuleWaitlist.objects.get_or_create(email=email)
    return redirect("/curriculum/?waitlisted=1")


def learners(request):
    return render(request, "pages/learners.html")


def start(request):
    return render(request, "pages/start.html")


def curriculum(request):
    return render(request, "pages/curriculum.html")


def curriculum_module_redirect(request, slug):
    return redirect(f"/curriculum/{slug}/", permanent=True)


def module_detail(request, slug):
    module = MODULES_BY_SLUG.get(slug)
    if module is None:
        raise Http404("Module not found")
    downloaded = request.GET.get("downloaded") == "1"
    return render(request, "pages/module_detail.html", {"module": module, "downloaded": downloaded})


def download_sample(request):
    if request.method != "POST":
        raise Http404()
    if request.POST.get("website"):
        return redirect("thank_you")
    email = (request.POST.get("email") or "").strip()
    slug = (request.POST.get("source") or "module-1-sample").strip()
    if email:
        CurriculumLead.objects.get_or_create(email=email, defaults={"source": slug})
        download_url = request.build_absolute_uri("/curriculum/sample-lesson.pdf")
        try:
            from django.core.mail import send_mail
            send_mail(
                subject="Your sample lesson — The School of Critical Thinking",
                message=f"Download your sample lesson here: {download_url}",
                from_email=None,
                recipient_list=[email],
                html_message=f"""<!DOCTYPE html>
<html><body style="font-family:Georgia,serif;max-width:600px;margin:0 auto;padding:40px 24px;color:#1a1a1a;line-height:1.7;">
<p>Hello,</p>
<p>Here is your sample lesson from <em>Seeing Patterns</em> — Module 1 of the School of Critical Thinking curriculum.</p>
<p><a href="{download_url}" style="display:inline-block;background:#111;color:#fff;padding:12px 24px;text-decoration:none;font-family:Arial,sans-serif;font-size:15px;font-weight:600;">Download sample lesson &rarr;</a></p>
<p style="font-size:13px;color:#888;">If the button doesn't work, copy this link: {download_url}</p>
<hr style="border:none;border-top:1px solid #ddd;margin:32px 0;">
<p style="font-size:13px;color:#888;">The School of Critical Thinking</p>
</body></html>""",
                fail_silently=True,
            )
        except Exception:
            pass
    return redirect("thank_you")


def thank_you(request):
    return render(request, "pages/thank-you.html")


def sample_pdf(request):
    import os
    # staticfiles/ is where WhiteNoise serves from in production; fall back to static/ in dev
    pdf_path = os.path.join(settings.BASE_DIR, "staticfiles", "Lessons", "Lesson_1.pdf")
    if not os.path.exists(pdf_path):
        pdf_path = os.path.join(settings.BASE_DIR, "static", "Lessons", "Lesson_1.pdf")
    response = FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Seeing_Patterns_Sample_Lesson.pdf"'
    return response


from django.urls import reverse


def contact(request):
    path = request.GET.get("path", "")  # "adult" / "parent" / ""
    source = request.GET.get("from", "")  # optional

    if request.method == "POST":
        # Honeypot: bots fill in hidden fields, humans don't
        if request.POST.get("website"):
            return redirect(f"{reverse('contact')}?sent=1&path={path}&from={source}")

        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        message = (request.POST.get("message") or "").strip()

        errors = {}
        if not name:
            errors["name"] = "Name is required."
        if not email:
            errors["email"] = "Email is required."
        if not message:
            errors["message"] = "Message is required."

        if not errors:
            ContactMessage.objects.create(
                name=name,
                email=email,
                message=message,
            )
            # Redirect to avoid duplicate submits on refresh
            return redirect(f"{reverse('contact')}?sent=1&path={path}&from={source}")

        return render(
            request,
            "pages/contact.html",
            {
                "path": path,
                "source": source,
                "errors": errors,
                "form": {"name": name, "email": email, "message": message},
            },
        )

    sent = request.GET.get("sent") == "1"
    return render(
        request,
        "pages/contact.html",
        {"path": path, "source": source, "sent": sent},
    )


def robots_txt(request):
    template = loader.get_template("robots.txt")
    return HttpResponse(template.render({}, request), content_type="text/plain")
