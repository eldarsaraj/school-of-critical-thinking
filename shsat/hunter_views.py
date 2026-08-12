"""
Hunter platform views — /hunter/ URL prefix.

All views here require platform='hunter' (staff bypass).
Shared test-taking views (test_take, test_submit, etc.) still live in views.py
but redirect to hunter_* URL names for Hunter tests.
"""

from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages

from .models import Parent, Test, TestAttempt, Answer
from .forms import SignupForm, LoginForm, NotesForm, AccountForm


# ---------------------------------------------------------------------------
# Platform guard
# ---------------------------------------------------------------------------

def _hunter_required(view_func):
    """Allow only Hunter-platform users (staff bypass). Redirects others."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/hunter/login/?next={request.path}")
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        try:
            parent = request.user.shsat_profile
        except Parent.DoesNotExist:
            return redirect(f"/hunter/login/?next={request.path}")
        if parent.platform != "hunter":
            return redirect("shsat_dashboard")
        return view_func(request, *args, **kwargs)
    return wrapped


def _get_hunter_parent(request):
    """Get or create Parent for the current user, defaulting to hunter platform."""
    parent, _ = Parent.objects.get_or_create(
        user=request.user,
        defaults={"platform": "hunter"},
    )
    return parent


def _send_hunter_verification_email(request, user, parent):
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    verify_url = request.build_absolute_uri(
        f"/shsat/verify-email/{parent.email_verification_token}/"
    )
    body = render_to_string("shsat/email_verify.html", {"verify_url": verify_url})
    send_mail(
        subject="Verify your email — Hunter Prep",
        message=f"Verify your email: {verify_url}",
        from_email=None,
        recipient_list=[user.email],
        html_message=body,
        fail_silently=True,
    )


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def hunter_landing(request):
    if request.user.is_authenticated:
        return redirect("hunter_dashboard")
    return render(request, "shsat/hunter_landing.html")


def hunter_signup(request):
    if request.user.is_authenticated:
        return redirect("hunter_dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        parent = Parent.objects.create(user=user, platform="hunter", email_verified=False)
        _send_hunter_verification_email(request, user, parent)
        user = authenticate(request, email=user.email, password=form.cleaned_data["password1"])
        if user:
            login(request, user, backend="shsat.backends.EmailBackend")
        return redirect("hunter_verify_pending")
    return render(request, "shsat/hunter_signup.html", {"form": form})


def hunter_login(request):
    if request.user.is_authenticated:
        return redirect("hunter_dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user, backend="shsat.backends.EmailBackend")
        next_url = request.GET.get("next")
        if next_url:
            return redirect(next_url)
        # Redirect based on platform
        try:
            if user.shsat_profile.platform == "shsat" and not user.is_staff:
                return redirect("shsat_dashboard")
        except Parent.DoesNotExist:
            pass
        return redirect("hunter_dashboard")
    return render(request, "shsat/hunter_login.html", {"form": form})


def hunter_logout(request):
    logout(request)
    return redirect("hunter_landing")


@_hunter_required
def hunter_verify_pending(request):
    try:
        parent = request.user.shsat_profile
        if parent.email_verified:
            return redirect("hunter_dashboard")
    except Parent.DoesNotExist:
        pass
    resent = request.GET.get("resent") == "1"
    return render(request, "shsat/hunter_verify_pending.html", {
        "email": request.user.email,
        "resent": resent,
    })


@_hunter_required
@require_POST
def hunter_verify_resend(request):
    try:
        parent = request.user.shsat_profile
        if not parent.email_verified:
            _send_hunter_verification_email(request, request.user, parent)
    except Parent.DoesNotExist:
        pass
    return redirect("/hunter/verify-email/?resent=1")


# ---------------------------------------------------------------------------
# Protected views
# ---------------------------------------------------------------------------

def _hunter_band(pct):
    """Map a percentage score to a (label, hex_color) band tuple."""
    if pct is None:
        return None, None
    if pct >= 85:
        return "Highly Competitive", "#2c6e8a"
    if pct >= 70:
        return "Competitive", "#5aab8c"
    if pct >= 50:
        return "Developing", "#c49a5a"
    return "Emerging", "#c4635b"


_SKILL_LABEL_MAP = {
    "main_idea": "Main Idea",
    "supporting_detail": "Supporting Detail",
    "evidence_selection": "Evidence",
    "inference": "Inference",
    "vocabulary": "Vocabulary",
    "authors_craft": "Author's Craft",
    "cross_passage_synthesis": "Cross-passage",
    "punctuation": "Punctuation",
    "usage_agreement": "Usage & Agreement",
    "sentence_structure": "Sentence Structure",
    "number_operations": "Number Ops",
    "ratios_proportions": "Ratios & Proportions",
    "algebra": "Algebra",
    "geometry": "Geometry",
    "statistics_data": "Statistics",
    "probability": "Probability",
    "multistep_word_problems": "Multi-step",
}

_RC_SECTIONS = {"reading_comprehension", "writing"}
_MATH_SECTIONS = {"quantitative_reasoning", "math_achievement"}


@_hunter_required
def hunter_dashboard(request):
    import json as _json
    from collections import defaultdict
    from evaluators.models import EssayEvaluation

    parent = _get_hunter_parent(request)

    if not parent.email_verified and not request.user.is_staff:
        return redirect("hunter_verify_pending")

    # All completed non-drill Hunter attempts, oldest first for charts
    attempts_asc = (
        TestAttempt.objects.filter(
            parent=parent, is_completed=True,
            test__is_drill=False, test__exam_type="hunter",
        )
        .select_related("test")
        .order_by("submitted_at")
    )
    attempts_desc = list(reversed(list(attempts_asc)))

    # Question counts per test per section (used for percentage scoring)
    from .models import Question as _Question
    from django.db.models import Count as _Count
    _test_ids = {a.test_id for a in attempts_desc}
    q_counts = {}
    for _row in (
        _Question.objects.filter(test_id__in=_test_ids)
        .values("test_id", "section")
        .annotate(n=_Count("id"))
    ):
        q_counts.setdefault(_row["test_id"], {})[_row["section"]] = _row["n"]

    # In-progress
    in_progress = (
        TestAttempt.objects.filter(parent=parent, is_completed=False, test__exam_type="hunter")
        .select_related("test")
        .order_by("-started_at")
        .first()
    )

    # Score history — tests with "baseline" in the title are collapsed to one entry;
    # others are labelled Benchmark 1, Benchmark 2, …
    baseline_entries = []
    benchmark_entries = []
    for a in attempts_asc:
        if a.composite_score is None:
            continue
        _tc = q_counts.get(a.test_id, {})
        _rc_tot = _tc.get("reading_comprehension", 0)
        _math_tot = _tc.get("quantitative_reasoning", 0) + _tc.get("math_achievement", 0)
        _comp_tot = _rc_tot + _math_tot
        entry = {
            "date": a.submitted_at.strftime("%b %d, %Y"),
            "rc": round(a.ela_correct / _rc_tot * 100) if _rc_tot and a.ela_correct is not None else None,
            "math": round(a.math_correct / _math_tot * 100) if _math_tot and a.math_correct is not None else None,
            "total": round(a.composite_score / _comp_tot * 100) if _comp_tot else None,
            "source": a.test.title,
        }
        if "baseline" in a.test.title.lower():
            baseline_entries.append(entry)
        else:
            benchmark_entries.append(entry)

    score_history = []
    if baseline_entries:
        e = baseline_entries[-1]  # most recent baseline attempt
        e["seq"] = "Baseline"
        score_history.append(e)
    for i, e in enumerate(benchmark_entries, 1):
        e["seq"] = f"Benchmark {i}"
        score_history.append(e)

    # Practice (drill) scores
    drill_attempts = (
        TestAttempt.objects.filter(
            parent=parent, is_completed=True,
            test__is_drill=True, test__exam_type="hunter",
        )
        .select_related("test")
        .order_by("submitted_at")
    )
    practice_chart_data = [
        {
            "label": f"{a.test.title} · {a.submitted_at.strftime('%b %d')}",
            "rc": a.ela_correct or 0,
            "math": a.math_correct or 0,
            "total": a.composite_score or 0,
        }
        for a in drill_attempts
        if a.composite_score is not None
    ]

    # Latest completed attempt for KPI
    latest_attempt = attempts_desc[0] if attempts_desc else None

    # Skill accuracy across all completed non-drill answers
    all_answers = list(
        Answer.objects.filter(
            attempt__parent=parent,
            attempt__is_completed=True,
            attempt__test__is_drill=False,
            attempt__test__exam_type="hunter",
            is_correct__isnull=False,
        ).select_related("question")
    )

    skill_stats = {}
    for ans in all_answers:
        if ans.question.question_type == "essay":
            continue
        skill = ans.question.skill or "unknown"
        section = ans.question.section
        if skill not in skill_stats:
            skill_stats[skill] = {
                "correct": 0, "total": 0,
                "time_sum": 0, "time_count": 0,
                "section": section,
            }
        skill_stats[skill]["total"] += 1
        if ans.is_correct:
            skill_stats[skill]["correct"] += 1
        if ans.time_spent_seconds:
            skill_stats[skill]["time_sum"] += ans.time_spent_seconds
            skill_stats[skill]["time_count"] += 1

    skill_accuracy_data = []
    for skill, s in skill_stats.items():
        if s["total"] == 0 or skill not in _SKILL_LABEL_MAP:
            continue
        pct = round(s["correct"] / s["total"] * 100, 1)
        avg_time = round(s["time_sum"] / s["time_count"] / 60, 2) if s["time_count"] > 0 else None
        skill_accuracy_data.append({
            "skill": skill,
            "label": _SKILL_LABEL_MAP[skill],
            "section": s["section"],
            "accuracy": pct,
            "correct": s["correct"],
            "total": s["total"],
            "avg_time": avg_time,
        })
    skill_accuracy_data.sort(key=lambda x: x["accuracy"])

    # Focus areas: 3 weakest skills with at least 3 answers
    focus_areas = [s for s in skill_accuracy_data if s["total"] >= 3][:3]

    # Avg time per question (non-essay)
    timed_answers = [
        a for a in all_answers
        if a.time_spent_seconds is not None and a.question.question_type != "essay"
    ]
    avg_time_per_q = (
        round(sum(a.time_spent_seconds for a in timed_answers) / len(timed_answers) / 60, 1)
        if timed_answers else None
    )

    # Essay evaluation (most recent)
    essay_eval = None
    try:
        latest_essay_answer = (
            Answer.objects.filter(
                attempt__parent=parent,
                attempt__is_completed=True,
                attempt__test__exam_type="hunter",
                question__question_type="essay",
            )
            .select_related("evaluation")
            .order_by("-attempt__submitted_at")
            .first()
        )
        if latest_essay_answer:
            ev = latest_essay_answer.evaluation
            if ev.succeeded:
                essay_eval = ev.evaluation_data
    except Exception:
        pass

    # Per-attempt percentage scores for the scores table
    attempts_with_pct = []
    for a in attempts_desc:
        tc = q_counts.get(a.test_id, {})
        rc_total = tc.get("reading_comprehension", 0)
        math_total = tc.get("quantitative_reasoning", 0) + tc.get("math_achievement", 0)
        comp_total = rc_total + math_total
        rc_pct = round(a.ela_correct / rc_total * 100) if rc_total and a.ela_correct is not None else None
        math_pct = round(a.math_correct / math_total * 100) if math_total and a.math_correct is not None else None
        comp_pct = round(a.composite_score / comp_total * 100) if comp_total and a.composite_score is not None else None
        comp_band, comp_color = _hunter_band(comp_pct)
        attempts_with_pct.append({
            "attempt": a,
            "rc_pct": rc_pct,
            "math_pct": math_pct,
            "comp_pct": comp_pct,
            "comp_band": comp_band,
            "comp_color": comp_color,
        })

    latest_composite_pct = attempts_with_pct[0]["comp_pct"] if attempts_with_pct else None
    latest_composite_band, latest_composite_color = _hunter_band(latest_composite_pct)

    context = {
        "parent": parent,
        "in_progress": in_progress,
        "attempts": attempts_desc,
        "attempts_with_pct": attempts_with_pct,
        "score_history": score_history,
        "score_history_json": _json.dumps(score_history),
        "practice_chart_data": practice_chart_data,
        "practice_chart_data_json": _json.dumps(practice_chart_data),
        "latest_attempt": latest_attempt,
        "latest_composite_pct": latest_composite_pct,
        "latest_composite_band": latest_composite_band,
        "latest_composite_color": latest_composite_color,
        "skill_accuracy_data": skill_accuracy_data,
        "skill_accuracy_json": _json.dumps(skill_accuracy_data),
        "focus_areas": focus_areas,
        "avg_time_per_q": avg_time_per_q,
        "has_timing_data": bool(timed_answers),
        "essay_eval": essay_eval,
        "tests_completed": len(attempts_desc),
    }
    return render(request, "shsat/hunter_dashboard.html", context)


@_hunter_required
def hunter_test_list(request):
    parent = _get_hunter_parent(request)

    if not parent.email_verified and not request.user.is_staff:
        return redirect("hunter_verify_pending")

    if request.user.is_staff:
        tests = Test.objects.filter(exam_type="hunter").order_by("order", "id")
    else:
        tests = Test.objects.filter(exam_type="hunter", is_published=True).order_by("order", "id")

    completed_ids = set(
        TestAttempt.objects.filter(parent=parent, is_completed=True).values_list("test_id", flat=True)
    )
    in_progress_ids = set(
        TestAttempt.objects.filter(parent=parent, is_completed=False).values_list("test_id", flat=True)
    )
    context = {
        "tests": tests,
        "completed_ids": completed_ids,
        "in_progress_ids": in_progress_ids,
    }
    return render(request, "shsat/hunter_test_list.html", context)


@_hunter_required
def hunter_resources(request):
    parent = _get_hunter_parent(request)
    if not parent.email_verified and not request.user.is_staff:
        return redirect("hunter_verify_pending")
    return render(request, "shsat/hunter_resources.html")


@_hunter_required
def hunter_account(request):
    parent = _get_hunter_parent(request)
    if not parent.email_verified and not request.user.is_staff:
        return redirect("hunter_verify_pending")
    form = AccountForm(request.POST or None, instance=parent, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account updated.")
        return redirect("hunter_account")
    completed_attempts = (
        TestAttempt.objects.filter(parent=parent, is_completed=True, test__exam_type="hunter")
        .select_related("test")
        .order_by("submitted_at")
    )
    return render(request, "shsat/hunter_account.html", {
        "form": form,
        "parent": parent,
        "completed_attempts": completed_attempts,
    })


@_hunter_required
def hunter_error_analysis_list(request):
    parent = _get_hunter_parent(request)
    if not parent.email_verified and not request.user.is_staff:
        return redirect("hunter_verify_pending")
    completed_attempts = (
        TestAttempt.objects.filter(parent=parent, is_completed=True, test__exam_type="hunter")
        .select_related("test")
        .order_by("-submitted_at")
    )
    return render(request, "shsat/hunter_error_analysis_list.html", {
        "parent": parent,
        "completed_attempts": completed_attempts,
    })


@_hunter_required
@require_POST
def hunter_delete_attempt(request, attempt_id):
    parent = _get_hunter_parent(request)
    attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent)
    attempt.delete()
    messages.success(request, "Test attempt deleted.")
    return redirect("hunter_account")
