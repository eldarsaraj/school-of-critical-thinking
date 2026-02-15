from __future__ import annotations

from pathlib import Path

import markdown
import yaml
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string

from diagnostic.data.v0_1.scoring import score_answers
from diagnostic.models import DiagnosticLead

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "v0_1"

QUESTIONS_PATH = DATA_DIR / "questions.yaml"
MODULES_PATH = DATA_DIR / "modules.yaml"
RESOURCES_PATH = DATA_DIR / "resources.yaml"
MODULE_PAGES_DIR = DATA_DIR / "module_pages"


def load_questions() -> list[dict]:
    with QUESTIONS_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["questions"]


def load_modules() -> list[dict]:
    with MODULES_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["modules"]


def load_resources() -> dict:
    with RESOURCES_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("resources", {})


def find_module_markdown_path(module_id: str) -> Path | None:
    if not MODULE_PAGES_DIR.exists():
        return None
    matches = sorted(MODULE_PAGES_DIR.glob(f"{module_id}_*.md"))
    return matches[0] if matches else None


def render_module_markdown(module_id: str) -> str:
    p = find_module_markdown_path(module_id)
    if not p:
        return ""
    md_text = p.read_text(encoding="utf-8")
    return markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables"],
        output_format="html5",
    )


def diagnostic_home(request: HttpRequest) -> HttpResponse:
    questions = load_questions()
    return render(request, "diagnostic/diagnostic_home.html", {"questions": questions})


def diagnostic_results(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("diagnostic_home")

    questions = load_questions()

    answers: dict[str, str] = {}
    for q in questions:
        qid = q["id"]
        choice = request.POST.get(qid)
        if choice:
            answers[qid] = choice

    result = score_answers(questions=questions, answers=answers, top_k=2)

    request.session["diagnostic_v0_1_top_breakpoints"] = list(result.top_breakpoints)

    modules = load_modules()
    by_breakpoint = {m["breakpoint"]: m for m in modules}

    selected_module_ids: list[str] = []
    for bp in result.top_breakpoints:
        m = by_breakpoint.get(bp)
        if m:
            selected_module_ids.append(m["id"])

    request.session["diagnostic_v0_1_module_ids"] = selected_module_ids

    return redirect("diagnostic_email")


def diagnostic_email(request: HttpRequest) -> HttpResponse:
    module_ids: list[str] = request.session.get("diagnostic_v0_1_module_ids", [])
    top_breakpoints: list[str] = request.session.get(
        "diagnostic_v0_1_top_breakpoints", []
    )

    if not module_ids:
        return redirect("diagnostic_home")

    modules = load_modules()
    by_id = {m["id"]: m for m in modules}
    by_breakpoint = {m["breakpoint"]: m for m in modules}

    preview_modules = []
    for mid in module_ids:
        m = by_id.get(mid)
        if m:
            preview_modules.append({"id": mid, "title": m.get("title", mid)})

    framing_lines = []
    for bp in top_breakpoints:
        m = by_breakpoint.get(bp)
        if not m:
            continue
        title = m.get("title", bp)
        goal = (m.get("goal") or "").strip()
        framing_lines.append(f"{title}: {goal}" if goal else title)

    if request.method == "POST":
        full_name = (request.POST.get("full_name") or "").strip()
        organization = (request.POST.get("organization") or "").strip()
        email = (request.POST.get("email") or "").strip()

        if full_name and email:
            request.session["diagnostic_v0_1_full_name"] = full_name
            request.session["diagnostic_v0_1_organization"] = organization
            request.session["diagnostic_v0_1_email"] = email

            try:
                DiagnosticLead.objects.create(
                    email=email,
                    full_name=full_name,
                    organization=organization,
                    module_ids=",".join(module_ids),
                    version="v0_1",
                )
            except TypeError:
                DiagnosticLead.objects.create(
                    email=email,
                    module_ids=",".join(module_ids),
                    version="v0_1",
                )

            return redirect("diagnostic_syllabus")

    return render(
        request,
        "diagnostic/diagnostic_email.html",
        {"preview_modules": preview_modules, "framing_lines": framing_lines},
    )


def diagnostic_syllabus(request: HttpRequest) -> HttpResponse:
    module_ids: list[str] = request.session.get("diagnostic_v0_1_module_ids", [])
    if not module_ids:
        return redirect("diagnostic_home")

    full_name = request.session.get("diagnostic_v0_1_full_name", "")
    organization = request.session.get("diagnostic_v0_1_organization", "")

    modules = load_modules()
    resources = load_resources()
    by_id = {m["id"]: m for m in modules}

    selected_modules: list[dict] = []
    for mid in module_ids:
        m = by_id.get(mid)
        if not m:
            continue
        m = dict(m)
        m["content_html"] = render_module_markdown(mid)
        m["resources"] = resources.get(mid, {})
        selected_modules.append(m)

    return render(
        request,
        "diagnostic/diagnostic_results.html",
        {
            "selected_modules": selected_modules,
            "full_name": full_name,
            "organization": organization,
        },
    )


def _wrap_words(text: str, max_chars: int) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    lines: list[str] = []
    cur: list[str] = []
    n = 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if n + add > max_chars:
            lines.append(" ".join(cur))
            cur = [w]
            n = len(w)
        else:
            cur.append(w)
            n += add
    if cur:
        lines.append(" ".join(cur))
    return lines


def _pdf_reportlab_fallback(
    *,
    module_ids: list[str],
    selected_modules: list[dict],
    full_name: str,
    organization: str,
) -> HttpResponse:
    # Local import so Django can boot even if ReportLab isn't installed somewhere
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="thinking-diagnostic.pdf"'

    c = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    x = 54
    y = height - 54
    line = 14

    def ensure_space():
        nonlocal y
        if y < 72:
            c.showPage()
            y = height - 54

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, "Thinking Diagnostic — Syllabus")
    y -= 2 * line

    c.setFont("Helvetica", 11)
    if full_name:
        c.drawString(x, y, f"Prepared for: {full_name}")
        y -= line
    if organization:
        c.drawString(x, y, f"Organization: {organization}")
        y -= line
    y -= line

    # Modules
    for m in selected_modules:
        ensure_space()
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x, y, m.get("title", m.get("id", "Module")))
        y -= 1.5 * line

        c.setFont("Helvetica", 11)
        goal = (m.get("goal") or "").strip()
        if goal:
            for chunk in _wrap_words(goal, 95):
                ensure_space()
                c.drawString(x, y, chunk)
                y -= line
            y -= line

        # Resources (titles only, compact)
        r = m.get("resources") or {}
        sections = [
            ("core_readings", "Core readings"),
            ("supporting", "Supporting"),
            ("video", "Video"),
            ("practice", "Practice"),
        ]
        for key, label in sections:
            items = r.get(key) or []
            if not items:
                continue
            ensure_space()
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x, y, f"{label}:")
            y -= line
            c.setFont("Helvetica", 10)
            for it in items:
                title = (it.get("title") or "Untitled").strip()
                author = (it.get("author") or "").strip()
                row = f"- {title}" + (f" — {author}" if author else "")
                for chunk in _wrap_words(row, 100):
                    ensure_space()
                    c.drawString(x + 12, y, chunk)
                    y -= line
            y -= line

        y -= line  # spacer between modules

    c.showPage()
    c.save()
    return response


def diagnostic_pdf(request: HttpRequest) -> HttpResponse:
    module_ids: list[str] = request.session.get("diagnostic_v0_1_module_ids", [])
    if not module_ids:
        return redirect("diagnostic_home")

    full_name = request.session.get("diagnostic_v0_1_full_name", "")
    organization = request.session.get("diagnostic_v0_1_organization", "")

    modules = load_modules()
    resources = load_resources()
    by_id = {m["id"]: m for m in modules}

    selected_modules: list[dict] = []
    for mid in module_ids:
        m = by_id.get(mid)
        if not m:
            continue
        m = dict(m)
        m["content_html"] = render_module_markdown(mid)
        m["resources"] = resources.get(mid, {})
        selected_modules.append(m)

    # Render HTML using your PDF template
    html_string = render_to_string(
        "diagnostic/diagnostic_pdf.html",
        {
            "selected_modules": selected_modules,
            "full_name": full_name,
            "organization": organization,
        },
        request=request,
    )

    # Primary: WeasyPrint (nice PDF). Fallback: ReportLab (always works).
    try:
        from weasyprint import HTML  # import here on purpose

        pdf_file = HTML(
            string=html_string,
            base_url=request.build_absolute_uri("/"),
        ).write_pdf()

        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = (
            'attachment; filename="thinking-diagnostic.pdf"'
        )
        return response

    except Exception:
        return _pdf_reportlab_fallback(
            module_ids=module_ids,
            selected_modules=selected_modules,
            full_name=full_name,
            organization=organization,
        )
