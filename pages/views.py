from django.shortcuts import render, redirect
from django.http import Http404, FileResponse, HttpResponse
from django.utils import timezone
from django.template import loader
from django.conf import settings


from .book_data import BOOKS
from .models import ContactMessage, CurriculumLead
from .module_data import MODULES_BY_SLUG


def home(request):
    return render(request, "pages/home.html")


def about(request):
    return render(request, "pages/about.html")


def books(request):
    return render(request, "pages/books.html", {"books": BOOKS})


def book_detail(request, slug):
    book = next((b for b in BOOKS if b.get("slug") == slug), None)
    if book is None:
        raise Http404("Book not found")

    return render(request, "pages/book_detail.html", {"book": book})


def start(request):
    return render(request, "pages/start.html")


def curriculum(request):
    return render(request, "pages/curriculum.html")


def module_detail(request, slug):
    module = MODULES_BY_SLUG.get(slug)
    if module is None:
        raise Http404("Module not found")
    downloaded = request.GET.get("downloaded") == "1"
    return render(request, "pages/module_detail.html", {"module": module, "downloaded": downloaded})


def download_sample(request):
    if request.method != "POST":
        raise Http404()
    email = (request.POST.get("email") or "").strip()
    slug = (request.POST.get("source") or "module-1-sample").strip()
    if email:
        CurriculumLead.objects.get_or_create(email=email, defaults={"source": slug})
    import os
    pdf_path = os.path.join(settings.BASE_DIR, "static", "Lessons", "Lesson_1.pdf")
    response = FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Seeing_Patterns_Sample_Lesson.pdf"'
    return response


from django.shortcuts import render, redirect
from django.urls import reverse

from .models import ContactMessage


def contact(request):
    path = request.GET.get("path", "")  # "adult" / "parent" / ""
    source = request.GET.get("from", "")  # optional

    if request.method == "POST":
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
