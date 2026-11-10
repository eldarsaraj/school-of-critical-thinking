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

from .models import Parent, Test, TestAttempt, Answer, TutorStudent
from .forms import SignupForm, LoginForm, NotesForm, AccountForm
from .views import _student_has_tutor_access


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
            # No Parent profile — log out to avoid redirect loop, then
            # send to login so they can use the right account
            logout(request)
            return redirect(f"/hunter/login/?next={request.path}")
        if parent.platform not in ("hunter", "both"):
            logout(request)
            return redirect(f"/hunter/login/?next={request.path}")
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
    body = render_to_string("shsat/email_verify_hunter.html", {"verify_url": verify_url})
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
    existing_shsat = False
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            existing_user = User.objects.get(email__iexact=email)
            existing_parent = existing_user.shsat_profile
            if existing_parent.platform == "shsat":
                existing_shsat = True
        except (User.DoesNotExist, Parent.DoesNotExist):
            pass
        if form.is_valid() and not existing_shsat:
            user = form.save()
            grade = form.cleaned_data.get("child_grade")
            signup_source = request.GET.get("source", "")[:50]
            parent = Parent.objects.create(
                user=user, platform="hunter", email_verified=False,
                child_grade=int(grade) if grade else None,
                signup_source=signup_source,
            )
            _send_hunter_verification_email(request, user, parent)
            user = authenticate(request, email=user.email, password=form.cleaned_data["password1"])
            if user:
                login(request, user, backend="shsat.backends.EmailBackend")
            return redirect("hunter_verify_pending")
    return render(request, "shsat/hunter_signup.html", {"form": form, "existing_shsat": existing_shsat})


def hunter_login(request):
    if request.user.is_authenticated:
        # Only redirect to hunter dashboard if user actually has hunter access
        if request.user.is_staff:
            return redirect("hunter_dashboard")
        try:
            parent = request.user.shsat_profile
            if parent.platform in ("hunter", "both"):
                return redirect("hunter_dashboard")
            # SHSAT-only user — log out so they see the Hunter login page
            logout(request)
        except Parent.DoesNotExist:
            # Logged in but no Parent profile (e.g. tutor) — log out so they
            # can log in with the right account instead of looping
            logout(request)
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user, backend="shsat.backends.EmailBackend")
        # Upgrade SHSAT-only users to "both" when they log in via Hunter
        try:
            parent = user.shsat_profile
            if parent.platform == "shsat":
                parent.platform = "both"
                parent.save(update_fields=["platform"])
        except Parent.DoesNotExist:
            # No Parent yet — create one with hunter platform
            Parent.objects.create(user=user, platform="hunter")
        return redirect(request.GET.get("next") or "hunter_dashboard")
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
    import re as _re
    from collections import defaultdict
    from evaluators.models import EssayEvaluation

    parent = _get_hunter_parent(request)

    if not parent.email_verified and not request.user.is_staff:
        return redirect("hunter_verify_pending")

    # All completed non-drill Hunter attempts, oldest first for charts
    attempts_asc = list(
        TestAttempt.objects.filter(
            parent=parent, is_completed=True,
            test__is_drill=False, test__exam_type="hunter",
        )
        .select_related("test")
        .order_by("submitted_at")
    )
    attempts_desc = list(reversed(attempts_asc))

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

    # ── Trap aggregation across all attempts ──
    from .forms import DISTRACTOR_CHOICES as _DC
    _dist_label = {}
    for entry in _DC:
        if isinstance(entry[1], (list, tuple)) and entry[0] not in ("",):
            for key, label in entry[1]:
                _dist_label[key] = label
        elif entry[0]:
            _dist_label[entry[0]] = entry[1]

    trap_aggregate = {}       # (section, label) -> count
    trap_by_attempt = {}      # attempt_id -> {(section, label): count}
    for ans in all_answers:
        if ans.selected_answer and not ans.is_correct:
            dt = ans.question.distractor_types or {}
            trap = dt.get(ans.selected_answer, "")
            if trap:
                section = ans.question.section or "unknown"
                raw_label = _dist_label.get(trap, trap.replace("_", " ").title())
                clean_label = _re.sub(r"^\([EM]\)\s*", "", raw_label)
                key = (section, clean_label)
                trap_aggregate[key] = trap_aggregate.get(key, 0) + 1
                trap_by_attempt.setdefault(ans.attempt_id, {})
                trap_by_attempt[ans.attempt_id][key] = trap_by_attempt[ans.attempt_id].get(key, 0) + 1

    total_wrong_rc = sum(v for (s, _), v in trap_aggregate.items() if s in _RC_SECTIONS)
    total_wrong_math = sum(v for (s, _), v in trap_aggregate.items() if s in _MATH_SECTIONS)

    dash_trap_data = sorted(
        [
            {
                "label": label,
                "section": section,
                "count": v,
                "pct": round(v / (total_wrong_rc if section in _RC_SECTIONS else total_wrong_math) * 100, 1)
                if (total_wrong_rc if section in _RC_SECTIONS else total_wrong_math) > 0
                else 0,
            }
            for (section, label), v in trap_aggregate.items()
        ],
        key=lambda x: x["count"], reverse=True,
    )

    top_trap_label = dash_trap_data[0]["label"] if dash_trap_data else None

    # ── Sankey data: RC + Math trap flow across tests ──
    _rc_traps = sorted(
        [(s, l, v) for (s, l), v in trap_aggregate.items() if s in _RC_SECTIONS],
        key=lambda x: x[2], reverse=True,
    )[:5]
    _math_traps = sorted(
        [(s, l, v) for (s, l), v in trap_aggregate.items() if s in _MATH_SECTIONS],
        key=lambda x: x[2], reverse=True,
    )[:5]

    def _build_sankey(traps_list):
        flows = []
        if not traps_list or not attempts_asc:
            return flows
        for a in attempts_asc:
            test_label = "Baseline" if a.test.title.lower().startswith("baseline") else a.test.title
            per_attempt = trap_by_attempt.get(a.id, {})
            for (section, label, _) in traps_list:
                flow = per_attempt.get((section, label), 0)
                if flow > 0:
                    flows.append({"from": test_label, "to": label, "flow": flow})
        return flows

    sankey_rc = _build_sankey(_rc_traps)
    sankey_math = _build_sankey(_math_traps)

    # ── Skill stats + per-attempt tracking for persistence ──
    skill_stats = {}
    att_skill_correct = defaultdict(lambda: defaultdict(int))
    att_skill_total = defaultdict(lambda: defaultdict(int))

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
        att_skill_total[ans.attempt_id][skill] += 1
        if ans.is_correct:
            att_skill_correct[ans.attempt_id][skill] += 1

    # Count how many attempts each skill was weak (< 70%) in
    skill_weak_counts = defaultdict(int)
    for att_id, totals in att_skill_total.items():
        for skill, total in totals.items():
            if total >= 2:
                correct = att_skill_correct[att_id].get(skill, 0)
                if correct / total < 0.70:
                    skill_weak_counts[skill] += 1

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

    # Annotate with persistence badges
    for s in skill_accuracy_data:
        weak_count = skill_weak_counts.get(s["skill"], 0)
        s["weak_attempts"] = weak_count
        s["is_persistent"] = weak_count >= 2

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

    # ── Attempts chart data (stacked bar + timing) ──
    attempts_chart_data = []
    for a in attempts_asc:
        if a.composite_score is None:
            continue
        tc = q_counts.get(a.test_id, {})
        rc_total = tc.get("reading_comprehension", 0)
        math_total = tc.get("quantitative_reasoning", 0) + tc.get("math_achievement", 0)
        rc_pct = round(a.ela_correct / rc_total * 100) if rc_total and a.ela_correct is not None else None
        math_pct = round(a.math_correct / math_total * 100) if math_total and a.math_correct is not None else None
        attempts_chart_data.append({
            "label": f"{a.test.title} · {a.submitted_at.strftime('%b %d')}",
            "rc": rc_pct or 0,
            "math": math_pct or 0,
            "total": round(a.composite_score / (rc_total + math_total) * 100) if (rc_total + math_total) else 0,
            "minutes": round(a.total_seconds / 60, 1) if a.total_seconds else None,
        })

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

    # Per-attempt percentage scores (kept for tooltip data)
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
        "attempts_chart_data": attempts_chart_data,
        "latest_attempt": latest_attempt,
        "latest_composite_pct": latest_composite_pct,
        "latest_composite_band": latest_composite_band,
        "latest_composite_color": latest_composite_color,
        "skill_accuracy_data": skill_accuracy_data,
        "focus_areas": focus_areas,
        "avg_time_per_q": avg_time_per_q,
        "has_timing_data": bool(timed_answers),
        "essay_eval": essay_eval,
        "tests_completed": len(attempts_desc),
        "dash_trap_data": dash_trap_data,
        "top_trap_label": top_trap_label,
        "sankey_rc": sankey_rc,
        "sankey_math": sankey_math,
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
        "hunter_has_paid": parent.hunter_has_paid or _student_has_tutor_access(parent) or request.user.is_staff,
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
    if attempt.is_completed:
        attempt.delete()
    else:
        attempt.is_abandoned = True
        attempt.save(update_fields=["is_abandoned"])
    messages.success(request, "Test attempt deleted.")
    return redirect("hunter_account")


def hunter_upgrade(request):
    from django.conf import settings as django_settings
    return render(request, "shsat/hunter_upgrade.html", {
        "stripe_publishable_key": django_settings.STRIPE_PUBLISHABLE_KEY,
    })


@login_required(login_url="/hunter/login/")
def hunter_create_checkout_session(request):
    import stripe
    from django.conf import settings as django_settings
    stripe.api_key = django_settings.STRIPE_SECRET_KEY

    parent, _ = Parent.objects.get_or_create(user=request.user)
    if parent.hunter_has_paid:
        return redirect("hunter_test_list")

    success_url = request.build_absolute_uri("/hunter/checkout/success/") + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.build_absolute_uri("/hunter/upgrade/")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": django_settings.STRIPE_HUNTER_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(request.user.id),
        customer_email=request.user.email,
        metadata={"parent_id": str(parent.id), "product_type": "hunter"},
    )
    return redirect(session.url, permanent=False)


@login_required(login_url="/hunter/login/")
def hunter_checkout_success(request):
    import stripe
    from django.conf import settings as django_settings
    session_id = request.GET.get("session_id")
    if session_id:
        stripe.api_key = django_settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                parent, _ = Parent.objects.get_or_create(user=request.user)
                if not parent.hunter_has_paid:
                    parent.hunter_has_paid = True
                    parent.save(update_fields=["hunter_has_paid"])
        except stripe.error.StripeError:
            pass
    return render(request, "shsat/hunter_checkout_success.html")


@login_required(login_url="/hunter/login/")
def hunter_checkout_cancel(request):
    return redirect("hunter_upgrade")


@login_required(login_url="/hunter/login/")
@require_POST
def add_shsat_access(request):
    parent = _get_hunter_parent(request)
    if parent.platform == "hunter":
        parent.platform = "both"
        parent.save(update_fields=["platform"])
    return redirect("shsat_dashboard")
