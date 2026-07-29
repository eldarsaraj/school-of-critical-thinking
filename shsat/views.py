from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

from .models import Parent, Test, Question, TestAttempt, Answer, ManualScore, CutoffScore, QuestionReport
from .forms import SignupForm, LoginForm, ManualScoreForm, NotesForm, AccountForm, QuestionEditForm, TestForm
from .scoring import scale_score, compute_placement


def _staff_required(view_func):
    """Decorator: only allow is_staff users, otherwise redirect to SHSAT login."""
    from functools import wraps
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/shsat/login/?next={request.path}")
        if not request.user.is_staff:
            return redirect("shsat_dashboard")
        return view_func(request, *args, **kwargs)
    return wrapped


def _require_shsat(view_func):
    """Decorator: allow only SHSAT-platform users (staff bypass). Redirects Hunter users."""
    from functools import wraps
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/shsat/login/?next={request.path}")
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        try:
            parent = request.user.shsat_profile
        except Parent.DoesNotExist:
            return view_func(request, *args, **kwargs)
        if parent.platform == "hunter":
            return redirect("hunter_dashboard")
        return view_func(request, *args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def landing(request):
    return render(request, "shsat/landing.html")


def terms(request):
    return render(request, "shsat/terms.html")


def upgrade(request):
    from django.conf import settings as django_settings
    return render(request, "shsat/upgrade.html", {
        "stripe_publishable_key": django_settings.STRIPE_PUBLISHABLE_KEY,
    })


@login_required(login_url="/shsat/login/")
def create_checkout_session(request):
    import stripe
    from django.conf import settings as django_settings
    stripe.api_key = django_settings.STRIPE_SECRET_KEY

    parent, _ = Parent.objects.get_or_create(user=request.user)
    if parent.has_paid:
        return redirect("shsat_test_list")

    success_url = request.build_absolute_uri("/shsat/checkout/success/") + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.build_absolute_uri("/shsat/upgrade/")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": django_settings.STRIPE_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(request.user.id),
        customer_email=request.user.email,
        metadata={"parent_id": str(parent.id)},
    )
    return redirect(session.url, permanent=False)


@login_required(login_url="/shsat/login/")
def checkout_success(request):
    import stripe
    from django.conf import settings as django_settings
    session_id = request.GET.get("session_id")
    if session_id:
        stripe.api_key = django_settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                parent, _ = Parent.objects.get_or_create(user=request.user)
                if not parent.has_paid:
                    parent.has_paid = True
                    parent.save(update_fields=["has_paid"])
        except stripe.error.StripeError:
            pass
    return render(request, "shsat/checkout_success.html")


@login_required(login_url="/shsat/login/")
def checkout_cancel(request):
    return redirect("shsat_upgrade")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    import stripe
    from django.conf import settings as django_settings
    stripe.api_key = django_settings.STRIPE_SECRET_KEY

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = django_settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event.type == "checkout.session.completed":
        session = event.data.object
        if getattr(session, "payment_status", None) == "paid":
            metadata = getattr(session, "metadata", None) or {}
            parent_id = metadata.get("parent_id") if hasattr(metadata, "get") else getattr(metadata, "parent_id", None)
            if parent_id:
                Parent.objects.filter(id=parent_id).update(has_paid=True)

    return HttpResponse(status=200)


def _send_verification_email(request, user, parent):
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    verify_url = request.build_absolute_uri(f"/shsat/verify-email/{parent.email_verification_token}/")
    body = render_to_string("shsat/email_verify.html", {"verify_url": verify_url})
    send_mail(
        subject="Verify your email — SHSAT Prep",
        message=f"Verify your email: {verify_url}",
        from_email=None,
        recipient_list=[user.email],
        html_message=body,
        fail_silently=True,
    )


def shsat_signup(request):
    if request.user.is_authenticated:
        return redirect("shsat_dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        parent = Parent.objects.create(user=user, platform="shsat", email_verified=False)
        _send_verification_email(request, user, parent)
        user = authenticate(request, email=user.email, password=form.cleaned_data["password1"])
        if user:
            login(request, user, backend="shsat.backends.EmailBackend")
        return redirect("shsat_verify_pending")
    return render(request, "shsat/signup.html", {"form": form})


@login_required(login_url="/shsat/login/")
def verify_pending(request):
    try:
        parent = request.user.shsat_profile
        if parent.email_verified:
            return redirect("shsat_dashboard")
    except Parent.DoesNotExist:
        pass
    resent = request.GET.get("resent") == "1"
    return render(request, "shsat/verify_pending.html", {
        "email": request.user.email,
        "resent": resent,
    })


@login_required(login_url="/shsat/login/")
@require_POST
def verify_resend(request):
    try:
        parent = request.user.shsat_profile
        if not parent.email_verified:
            _send_verification_email(request, request.user, parent)
    except Parent.DoesNotExist:
        pass
    return redirect("/shsat/verify-email/?resent=1")


def verify_email(request, token):
    parent = get_object_or_404(Parent, email_verification_token=token)
    parent.email_verified = True
    parent.save(update_fields=["email_verified"])
    if not request.user.is_authenticated:
        login(request, parent.user, backend="shsat.backends.EmailBackend")
    if parent.platform == "hunter":
        return redirect("hunter_dashboard")
    return redirect("shsat_dashboard")


def shsat_login(request):
    if request.user.is_authenticated:
        # Redirect Hunter users away from SHSAT login
        try:
            if request.user.shsat_profile.platform == "hunter" and not request.user.is_staff:
                return redirect("hunter_dashboard")
        except Parent.DoesNotExist:
            pass
        return redirect("shsat_dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user, backend="shsat.backends.EmailBackend")
        # Redirect Hunter-platform users to their dashboard
        try:
            if user.shsat_profile.platform == "hunter" and not user.is_staff:
                return redirect("hunter_dashboard")
        except Parent.DoesNotExist:
            pass
        return redirect(request.GET.get("next") or "shsat_dashboard")
    return render(request, "shsat/login.html", {"form": form})


def shsat_logout(request):
    logout(request)
    return redirect("shsat_landing")


@_require_shsat
def resources(request):
    return render(request, "shsat/resources.html")


# ---------------------------------------------------------------------------
# Protected views
# ---------------------------------------------------------------------------

@_require_shsat
def dashboard(request):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    attempts = (
        TestAttempt.objects.filter(parent=parent, is_completed=True, test__is_drill=False)
        .select_related("test")
        .order_by("-submitted_at")
    )
    manual_scores = ManualScore.objects.filter(parent=parent).order_by("-date")
    from django.db.models import Max
    latest_year = CutoffScore.objects.aggregate(Max("admissions_year"))["admissions_year__max"]
    cutoffs = CutoffScore.objects.filter(admissions_year=latest_year).order_by("cutoff_score")

    # Build score history for Chart.js (combined platform + manual)
    # Sort by full datetime so same-day tests appear in submission order
    from .scoring import scale_score as _scale
    score_history_raw = []
    for a in attempts:
        if a.composite_score is not None:
            score_history_raw.append({
                "_sort": a.submitted_at.isoformat(),
                "type": "attempt",
                "date": a.submitted_at.strftime("%b %d"),
                "composite": a.composite_score,
                "ela": a.ela_scaled,
                "math": a.math_scaled,
                "source": a.test.title,
            })
    for m in manual_scores:
        ela_scaled = _scale(min(m.ela_correct, 47))
        math_scaled = _scale(min(m.math_correct, 47))
        score_history_raw.append({
            "_sort": m.date.isoformat() + "T00:00:00",
            "type": "manual",
            "date": m.date.strftime("%b %d"),
            "composite": ela_scaled + math_scaled,
            "ela": ela_scaled,
            "math": math_scaled,
            "source": m.source_name,
        })
    score_history_raw.sort(key=lambda x: x["_sort"])
    # Collapse all "Baseline Test" entries into a single point (latest score wins).
    # Everything else is labelled "Test 1", "Test 2", … in chronological order.
    baseline_entries = [e for e in score_history_raw if "baseline" in e["source"].lower()]
    other_entries = [e for e in score_history_raw if "baseline" not in e["source"].lower()]
    collapsed = []
    if baseline_entries:
        best = baseline_entries[-1]  # most recent Baseline attempt
        best["seq"] = "Baseline"
        collapsed.append(best)
    test_count = 0
    log_count = 0
    for entry in other_entries:
        if entry.get("type") == "manual":
            log_count += 1
            entry["seq"] = f"Log {log_count}"
        else:
            test_count += 1
            entry["seq"] = f"Benchmark {test_count}"
        collapsed.append(entry)
    score_history_raw = collapsed
    score_history = [{k: v for k, v in e.items() if k != "_sort"} for e in score_history_raw]

    # Most recent composite = from the most recently submitted attempt (not mixed history)
    latest_attempt = attempts.filter(composite_score__isnull=False).first()
    latest_composite = latest_attempt.composite_score if latest_attempt else None

    placement_data = compute_placement(latest_composite, cutoffs) if latest_composite else []

    cutoffs_list = [
        {"school_short": c.school_short, "cutoff": c.cutoff_score}
        for c in cutoffs
    ]
    attempts_chart_data = [
        {
            "label": f"{a.test.title} · {a.submitted_at.strftime('%b %d')}",
            "ela": a.ela_scaled,
            "math": a.math_scaled,
            "composite": a.composite_score,
            "minutes": round(a.total_seconds / 60, 1) if a.total_seconds else None,
        }
        for a in reversed(list(attempts))
        if a.composite_score is not None
    ]

    # Skill & difficulty accuracy aggregation (across all completed attempts)
    all_answers = Answer.objects.filter(
        attempt__parent=parent,
        attempt__is_completed=True,
        attempt__test__is_drill=False,
        is_correct__isnull=False,
    ).select_related("question")

    skill_stats = {}   # skill -> {correct, total, time_sum, time_count, section}
    # Per-attempt skill tracking for consistency analysis
    from collections import defaultdict
    att_skill_correct = defaultdict(lambda: defaultdict(int))
    att_skill_total   = defaultdict(lambda: defaultdict(int))

    for ans in all_answers:
        skill = ans.question.skill or "unknown"
        section = ans.question.section or "unknown"

        if skill not in skill_stats:
            skill_stats[skill] = {"correct": 0, "total": 0, "time_sum": 0, "time_count": 0, "section": section}
        skill_stats[skill]["total"] += 1
        if ans.is_correct:
            skill_stats[skill]["correct"] += 1
        if ans.time_spent_seconds is not None:
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


    # Sort skills by accuracy ascending (weakest first)
    skill_label_map = {
        # ELA — SKILL_CHOICES keys
        "punctuation": "Punctuation",
        "usage_agreement": "Usage & Agreement",
        "sentence_structure": "Sentence Structure",
        "main_idea": "Main Idea",
        "supporting_detail": "Supporting Detail",
        "evidence_selection": "Evidence",
        "inference": "Inference",
        "vocabulary": "Vocabulary",
        "authors_craft": "Author's Craft",
        "cross_passage_synthesis": "Cross-passage",
        # Math — SKILL_CHOICES keys
        "number_operations": "Number Ops",
        "ratios_proportions": "Ratios & Proportions",
        "algebra": "Algebra",
        "geometry": "Geometry",
        "statistics_data": "Statistics",
        "probability": "Probability",
        "multistep_word_problems": "Multi-step",
        # Legacy keys
        "grammar_mechanics": "Grammar",
        "rhetoric_organization": "Rhetoric",
        "literal_comprehension": "Comprehension",
        "inference_analysis": "Inference",
        "algebraic_reasoning": "Algebra",
        "geometric_reasoning": "Geometry",
        "data_probability": "Statistics",
        "multistep_reasoning": "Multi-step",
        "fractions_decimals_percents": "Fractions & Percents",
        "functions_patterns": "Functions",
        "unknown": "Other",
    }

    skill_accuracy_data = []
    for skill, s in skill_stats.items():
        if s["total"] == 0:
            continue
        # Skip skills not in the taxonomy (e.g. figurative_craft, unknown)
        if skill not in skill_label_map:
            continue
        raw_label = skill_label_map[skill]
        # Clean any residual underscores in labels
        label = raw_label.replace("_", " ").title() if "_" in raw_label else raw_label
        pct = round(s["correct"] / s["total"] * 100, 1)
        avg_time = round(s["time_sum"] / s["time_count"] / 60, 2) if s["time_count"] > 0 else None
        skill_accuracy_data.append({
            "skill": skill,
            "label": label,
            "section": s["section"],
            "accuracy": pct,
            "correct": s["correct"],
            "total": s["total"],
            "avg_time": avg_time,
        })
    skill_accuracy_data.sort(key=lambda x: x["accuracy"])

    # Annotate with persistence
    for s in skill_accuracy_data:
        weak_count = skill_weak_counts.get(s["skill"], 0)
        s["weak_attempts"] = weak_count
        s["is_persistent"] = weak_count >= 2

    weakest_skill = skill_accuracy_data[0]["label"] if skill_accuracy_data else None

    # Avg time per question across all timed answers
    timed_answers = [a for a in all_answers if a.time_spent_seconds is not None]
    has_timing_data = len(timed_answers) > 0
    avg_time_per_q = (
        round(sum(a.time_spent_seconds for a in timed_answers) / len(timed_answers) / 60, 1)
        if timed_answers else None
    )

    # Platform score distribution (all completed attempts across all users)
    import math as _math
    all_platform_scores = list(
        TestAttempt.objects.filter(is_completed=True, composite_score__isnull=False, test__is_drill=False)
        .values_list("composite_score", flat=True)
    )
    platform_n = len(all_platform_scores)
    if platform_n >= 5:
        platform_mean = sum(all_platform_scores) / platform_n
        variance = sum((s - platform_mean) ** 2 for s in all_platform_scores) / platform_n
        platform_std = round(max(_math.sqrt(variance), 20), 1)
        platform_mean = round(platform_mean, 1)
    else:
        platform_mean = None
        platform_std = None

    context = {
        "parent": parent,
        "attempts": attempts[:5],
        "manual_scores": manual_scores[:5],
        "score_history": score_history,
        "latest_composite": latest_composite,
        "placement_data": placement_data,
        "cutoffs": cutoffs,
        "cutoffs_list": cutoffs_list,
        "attempts_chart_data": attempts_chart_data,
        "skill_accuracy_data": skill_accuracy_data,
        "weakest_skill": weakest_skill,
        "avg_time_per_q": avg_time_per_q,
        "has_timing_data": has_timing_data,
        "platform_mean": platform_mean,
        "platform_std": platform_std,
        "platform_n": platform_n,
    }
    return render(request, "shsat/dashboard.html", context)


@login_required(login_url="/shsat/login/")
def log_score(request):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    form = ManualScoreForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        score = form.save(commit=False)
        score.parent = parent
        score.save()
        messages.success(request, "Score logged.")
        return redirect("shsat_log_score")
    logged_scores = ManualScore.objects.filter(parent=parent).order_by("-date")
    return render(request, "shsat/log_score.html", {"form": form, "logged_scores": logged_scores})


@login_required(login_url="/shsat/login/")
@require_POST
def delete_manual_score(request, score_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    score = get_object_or_404(ManualScore, id=score_id, parent=parent)
    score.delete()
    messages.success(request, "Score deleted.")
    return redirect("shsat_log_score")


@_require_shsat
def test_list(request):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    can_access_paid = parent.has_paid or request.user.is_staff

    if can_access_paid:
        tests = (
            Test.objects.filter(is_published=True) | Test.objects.filter(is_published=False, is_free=False)
        ).filter(is_drill=False, exam_type="shsat").distinct().order_by("id")
        drills = Test.objects.filter(is_drill=True, exam_type="shsat").order_by("order", "id")
    else:
        tests = Test.objects.filter(is_published=True, is_drill=False, exam_type="shsat")
        drills = Test.objects.filter(is_drill=True, exam_type="shsat")  # shown as locked teasers

    completed_ids = set(
        TestAttempt.objects.filter(parent=parent, is_completed=True).values_list("test_id", flat=True)
    )
    has_completed_any = bool(completed_ids)
    free_limit = settings.SHSAT_FREE_TEST_LIMIT
    tests_taken = TestAttempt.objects.filter(parent=parent, is_completed=True).count()
    context = {
        "tests": tests,
        "drills": drills,
        "completed_ids": completed_ids,
        "has_completed_any": has_completed_any,
        "free_limit": free_limit,
        "tests_taken": tests_taken,
        "has_paid": parent.has_paid,
        "can_access_paid": can_access_paid,
    }
    return render(request, "shsat/test_list.html", context)


@login_required(login_url="/shsat/login/")
def test_intro(request, test_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    test = get_object_or_404(Test, id=test_id)
    # Platform guard: ensure user can only access tests for their platform
    if not request.user.is_staff and test.exam_type != parent.platform:
        if parent.platform == "hunter":
            return redirect("hunter_test_list")
        return redirect("shsat_test_list")
    if not test.is_published and not test.is_free and not parent.has_paid and not request.user.is_staff:
        from django.http import Http404
        raise Http404
    in_progress = TestAttempt.objects.filter(parent=parent, test=test, is_completed=False).first()
    completed_attempt = TestAttempt.objects.filter(parent=parent, test=test, is_completed=True).order_by("-submitted_at").first()
    is_hunter_test = test.exam_type == "hunter"
    context = {
        "test": test,
        "in_progress": in_progress,
        "completed_attempt": completed_attempt if not request.user.is_staff else None,
        "ela_count": test.ela_questions().count(),
        "math_count": test.math_questions().count(),
        "duration_hours": settings.SHSAT_TEST_DURATION_SECONDS // 3600,
        "is_drill": test.is_drill,
        "parent_template": "shsat/base_hunter.html" if is_hunter_test else "shsat/base_shsat.html",
        # URL names so the template works for both platforms
        "url_test_take": "hunter_test_take" if is_hunter_test else "shsat_test_take",
        "url_test_list": "hunter_test_list" if is_hunter_test else "shsat_test_list",
        "url_test_results": "hunter_test_results" if is_hunter_test else "shsat_test_results",
    }
    if is_hunter_test:
        context["hunter_sections"] = [
            ("Reading Comprehension", test.questions.filter(section="reading_comprehension").count()),
            ("Writing", test.questions.filter(section="writing").count()),
            ("Quantitative Reasoning", test.questions.filter(section="quantitative_reasoning").count()),
            ("Math Achievement", test.questions.filter(section="math_achievement").count()),
        ]
    return render(request, "shsat/test_intro.html", context)


@login_required(login_url="/shsat/login/")
def test_take(request, test_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    test = get_object_or_404(Test, id=test_id)
    # Platform guard
    if not request.user.is_staff and test.exam_type != parent.platform:
        if parent.platform == "hunter":
            return redirect("hunter_test_list")
        return redirect("shsat_test_list")
    if not test.is_published and not test.is_free and not parent.has_paid and not request.user.is_staff:
        from django.http import Http404
        raise Http404

    # Block retake: if already completed, send to results (staff bypass)
    completed_attempt = TestAttempt.objects.filter(parent=parent, test=test, is_completed=True).order_by("-submitted_at").first()
    attempt = TestAttempt.objects.filter(parent=parent, test=test, is_completed=False).first()
    if not attempt:
        if completed_attempt and not request.user.is_staff:
            from django.contrib import messages
            messages.info(request, f"You have already completed {test.title}.")
            results_url = "hunter_test_results" if test.exam_type == "hunter" else "shsat_test_results"
            return redirect(results_url, attempt_id=completed_attempt.id)
        if test.exam_type == "hunter":
            HUNTER_SECTION_ORDER = ["reading_comprehension", "writing", "quantitative_reasoning", "math_achievement"]
            question_ids = []
            for sec in HUNTER_SECTION_ORDER:
                question_ids += list(test.questions.filter(section=sec).order_by('question_number').values_list('id', flat=True))
        else:
            # Determine section order from GET param (ELA first by default)
            section_first = request.GET.get("section_first", "ELA")
            second = "Math" if section_first == "ELA" else "ELA"
            if test.is_adaptive:
                # Routing questions in chosen section order
                first_ids = list(test.questions.filter(stage='routing', section=section_first).order_by('question_number').values_list('id', flat=True))
                second_ids = list(test.questions.filter(stage='routing', section=second).order_by('question_number').values_list('id', flat=True))
                question_ids = first_ids + second_ids
            else:
                first_ids = list(test.questions.filter(section=section_first).order_by('question_number').values_list('id', flat=True))
                second_ids = list(test.questions.filter(section=second).order_by('question_number').values_list('id', flat=True))
                question_ids = first_ids + second_ids
        attempt = TestAttempt.objects.create(
            parent=parent,
            test=test,
            started_with=question_ids,
        )
        for qid in question_ids:
            Answer.objects.get_or_create(attempt=attempt, question_id=qid)

    # Preserve question order from started_with (respects section choice and module insertions)
    qs_by_id = {q.id: q for q in Question.objects.filter(id__in=attempt.started_with)}
    ordered_questions = [qs_by_id[qid] for qid in attempt.started_with if qid in qs_by_id]

    # If started_with is non-empty but no questions resolved, the attempt has stale IDs
    # (e.g. test was re-imported with --replace). Reset so a fresh attempt is created.
    if attempt.started_with and not ordered_questions:
        attempt.delete()
        intro_url = "hunter_test_intro" if test.exam_type == "hunter" else "shsat_test_intro"
        return redirect(intro_url, test_id=test.id)

    answers_qs = Answer.objects.filter(attempt=attempt).select_related("question")
    answers_map = {a.question_id: a for a in answers_qs}

    # Build serializable question list for JSON rendering in JS
    # Track per-section display index (1-based sequential)
    section_counters = {s: 0 for s in set(q.section for q in ordered_questions)}
    q_list = []
    for q in ordered_questions:
        ans = answers_map.get(q.id)
        section_counters[q.section] += 1
        q_list.append({
            "id": q.id,
            "section": q.section,
            "stage": q.stage,
            "is_routing": q.stage == "routing",
            "question_number": q.question_number,
            "display_index": section_counters[q.section],
            "question_type": q.question_type,
            "use_efgh": test.exam_type == "shsat" and q.question_number % 2 == 0,
            "passage_group_id": q.passage_group_id or "",
            "passage_title": q.passage_title,
            "passage_text": q.passage_text,
            "image_url": q.image.url if q.image else "",
            "question_text": q.question_text,
            "choice_a": q.choice_a,
            "choice_b": q.choice_b,
            "choice_c": q.choice_c,
            "choice_d": q.choice_d,
            "choice_e": q.choice_e,
            "selected": ans.selected_answer if ans else "",
            "is_flagged": ans.is_flagged if ans else False,
        })

    elapsed = int((timezone.now() - attempt.started_at).total_seconds())
    remaining = max(0, settings.SHSAT_TEST_DURATION_SECONDS - elapsed)

    # Auto-submit if time has expired (e.g. user started a test and never returned)
    if remaining == 0:
        answers = Answer.objects.filter(attempt=attempt).select_related("question")
        for ans in answers:
            q = ans.question
            if q.question_type == "essay":
                continue
            if ans.selected_answer:
                ans.is_correct = ans.selected_answer.upper() == q.correct_answer.upper()
                ans.save(update_fields=["is_correct"])
        scored = list(Answer.objects.filter(attempt=attempt, is_correct__isnull=False))
        if test.exam_type == "hunter":
            rc_correct = sum(1 for a in scored if a.is_correct and a.question.section == "reading_comprehension")
            qr_correct = sum(1 for a in scored if a.is_correct and a.question.section == "quantitative_reasoning")
            ma_correct = sum(1 for a in scored if a.is_correct and a.question.section == "math_achievement")
            attempt.ela_correct = rc_correct
            attempt.math_correct = qr_correct + ma_correct
            attempt.ela_scaled = rc_correct
            attempt.math_scaled = qr_correct + ma_correct
            attempt.composite_score = rc_correct + qr_correct + ma_correct
        else:
            ela_correct = sum(1 for a in scored if a.is_correct and a.question.section == "ELA")
            math_correct = sum(1 for a in scored if a.is_correct and a.question.section == "Math")
            if attempt.test.is_adaptive and (attempt.ela_module or attempt.math_module):
                from .scoring import scale_score_adaptive
                ela_scaled = scale_score_adaptive(ela_correct, attempt.ela_module or 'easy')
                math_scaled = scale_score_adaptive(math_correct, attempt.math_module or 'easy')
            else:
                ela_scaled = scale_score(min(ela_correct, 47))
                math_scaled = scale_score(min(math_correct, 47))
            attempt.ela_correct = ela_correct
            attempt.math_correct = math_correct
            attempt.ela_scaled = ela_scaled
            attempt.math_scaled = math_scaled
            attempt.composite_score = ela_scaled + math_scaled
        attempt.is_completed = True
        attempt.submitted_at = timezone.now()
        attempt.total_seconds = elapsed
        attempt.save()
        _results_url = "hunter_test_results" if test.exam_type == "hunter" else "shsat_test_results"
        return redirect(_results_url, attempt_id=attempt.id)

    modules_assigned = bool(attempt.ela_module)

    context = {
        "test": test,
        "attempt": attempt,
        "q_list": q_list,
        "remaining_seconds": remaining,
        "duration_seconds": settings.SHSAT_TEST_DURATION_SECONDS,
        "is_adaptive": test.is_adaptive,
        "modules_assigned": modules_assigned,
        "ela_module": attempt.ela_module,
        "math_module": attempt.math_module,
    }
    template = "shsat/test_take_hunter.html" if test.exam_type == "hunter" else "shsat/test_take_shsat.html"
    return render(request, template, context)


@login_required(login_url="/shsat/login/")
@require_POST
def test_submit(request, test_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    # If already completed (double-submit), redirect to results gracefully
    completed = TestAttempt.objects.filter(test_id=test_id, parent=parent, is_completed=True).order_by("-submitted_at").first()
    if completed and not TestAttempt.objects.filter(test_id=test_id, parent=parent, is_completed=False).exists():
        _r = "hunter_test_results" if completed.test.exam_type == "hunter" else "shsat_test_results"
        return redirect(_r, attempt_id=completed.id)
    attempt = get_object_or_404(TestAttempt, test_id=test_id, parent=parent, is_completed=False)

    answers = Answer.objects.filter(attempt=attempt).select_related("question")

    for ans in answers:
        q = ans.question
        if q.question_type == "essay":
            continue
        if ans.selected_answer:
            correct = ans.selected_answer.upper() == q.correct_answer.upper()
            ans.is_correct = correct
            ans.save(update_fields=["is_correct"])

    scored = list(answers.filter(is_correct__isnull=False))

    if attempt.test.exam_type == "hunter":
        rc_correct = sum(1 for a in scored if a.is_correct and a.question.section == "reading_comprehension")
        qr_correct = sum(1 for a in scored if a.is_correct and a.question.section == "quantitative_reasoning")
        ma_correct = sum(1 for a in scored if a.is_correct and a.question.section == "math_achievement")
        ela_correct = rc_correct
        math_correct = qr_correct + ma_correct
        ela_scaled = rc_correct
        math_scaled = qr_correct + ma_correct
        composite = rc_correct + qr_correct + ma_correct
    else:
        ela_correct = sum(1 for a in scored if a.is_correct and a.question.section == "ELA")
        math_correct = sum(1 for a in scored if a.is_correct and a.question.section == "Math")
        if attempt.test.is_adaptive and (attempt.ela_module or attempt.math_module):
            from .scoring import scale_score_adaptive
            ela_scaled = scale_score_adaptive(ela_correct, attempt.ela_module or 'easy')
            math_scaled = scale_score_adaptive(math_correct, attempt.math_module or 'easy')
        else:
            ela_scaled = scale_score(min(ela_correct, 47))
            math_scaled = scale_score(min(math_correct, 47))
        composite = ela_scaled + math_scaled

    elapsed = int((timezone.now() - attempt.started_at).total_seconds())

    attempt.ela_correct = ela_correct
    attempt.math_correct = math_correct
    attempt.ela_scaled = ela_scaled
    attempt.math_scaled = math_scaled
    attempt.composite_score = composite
    attempt.is_completed = True
    attempt.submitted_at = timezone.now()
    attempt.total_seconds = elapsed
    attempt.save()

    # Send results email to parent (SHSAT only)
    if attempt.test.exam_type == "hunter":
        return redirect("hunter_test_results", attempt_id=attempt.id)

    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        error_analysis_url = request.build_absolute_uri(
            f"/shsat/tests/{attempt.id}/error-analysis/"
        )
        ela_total = answers.filter(question__section="ELA").count()
        math_total = answers.filter(question__section="Math").count()
        body = render_to_string("shsat/email_results.html", {
            "test_title": attempt.test.title,
            "ela_correct": ela_correct,
            "math_correct": math_correct,
            "ela_total": ela_total,
            "math_total": math_total,
            "composite_score": composite,
            "error_analysis_url": error_analysis_url,
            "is_baseline": attempt.test.is_free,
            "upgrade_url": request.build_absolute_uri("/shsat/upgrade/"),
        })
        send_mail(
            subject=f"Results ready: {attempt.test.title}",
            message="",
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[request.user.email],
            html_message=body,
            fail_silently=True,
        )
    except Exception:
        pass

    return redirect("shsat_test_results", attempt_id=attempt.id)
    # Note: Hunter tests return early above (hunter_test_results)


@login_required(login_url="/shsat/login/")
def test_results(request, attempt_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent, is_completed=True)
    answers = (
        Answer.objects.filter(attempt=attempt)
        .select_related("question")
        .order_by("question__section", "question__question_number")
    )
    cutoffs = CutoffScore.objects.all()
    placement_data = compute_placement(attempt.composite_score, cutoffs)

    notes_form = NotesForm(request.POST or None, initial={"notes": attempt.notes})
    is_hunter = attempt.test.exam_type == "hunter"
    if request.method == "POST" and notes_form.is_valid():
        attempt.notes = notes_form.cleaned_data["notes"]
        attempt.save(update_fields=["notes"])
        _r = "hunter_test_results" if is_hunter else "shsat_test_results"
        return redirect(_r, attempt_id=attempt.id)

    if is_hunter:
        ela_answers = [a for a in answers if a.question.section == "reading_comprehension"]
        math_answers = [a for a in answers if a.question.section in ("quantitative_reasoning", "math_achievement")]
        hunter_rc_answers = [a for a in answers if a.question.section == "reading_comprehension"]
        hunter_qr_answers = [a for a in answers if a.question.section == "quantitative_reasoning"]
        hunter_ma_answers = [a for a in answers if a.question.section == "math_achievement"]
        hunter_writing_answers = [a for a in answers if a.question.section == "writing"]
    else:
        order_map = {qid: i for i, qid in enumerate(attempt.started_with or [])}
        ela_answers = sorted(
            [a for a in answers if a.question.section == "ELA"],
            key=lambda a: order_map.get(a.question_id, 9999),
        )
        math_answers = sorted(
            [a for a in answers if a.question.section == "Math"],
            key=lambda a: order_map.get(a.question_id, 9999),
        )
        hunter_rc_answers = hunter_qr_answers = hunter_ma_answers = hunter_writing_answers = []

    flagged_answers = [a for a in answers if a.is_flagged]

    context = {
        "attempt": attempt,
        "ela_answers": ela_answers,
        "math_answers": math_answers,
        "flagged_answers": flagged_answers,
        "placement_data": placement_data,
        "notes_form": notes_form,
        "is_baseline": attempt.test.is_free,
        "is_drill": attempt.test.is_drill,
        "has_paid": parent.has_paid,
        "is_hunter": is_hunter,
        "hunter_rc_answers": hunter_rc_answers,
        "hunter_qr_answers": hunter_qr_answers,
        "hunter_ma_answers": hunter_ma_answers,
        "hunter_writing_answers": hunter_writing_answers,
        "hunter_qr_ma_total": len(hunter_qr_answers) + len(hunter_ma_answers),
        "parent_template": "shsat/base_hunter.html" if is_hunter else "shsat/base_shsat.html",
    }
    template = "shsat/test_results_hunter.html" if is_hunter else "shsat/test_results_shsat.html"
    return render(request, template, context)


@_require_shsat
def error_analysis_list(request):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    completed_attempts = (
        TestAttempt.objects.filter(parent=parent, is_completed=True, test__exam_type="shsat")
        .select_related("test")
        .order_by("-submitted_at")
    )
    return render(request, "shsat/error_analysis_list.html", {
        "parent": parent,
        "completed_attempts": completed_attempts,
    })


def _parse_quant_comparison(question_text):
    """Parse a quant_comparison question_text into structured fields for the template."""
    is_qc = "\nColumn A:" in question_text
    if not is_qc:
        return {"is_quant_comparison": False, "qc_col_a": "", "qc_col_b": "", "qc_shared": ""}
    col_a = col_b = shared = ""
    for line in question_text.splitlines():
        if line.startswith("Column A:"):
            col_a = line[9:].strip()
        elif line.startswith("Column B:"):
            col_b = line[9:].strip()
        elif line.strip():
            shared = line.strip()
    return {"is_quant_comparison": True, "qc_col_a": col_a, "qc_col_b": col_b, "qc_shared": shared}


@login_required(login_url="/shsat/login/")
def error_analysis(request, attempt_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent, is_completed=True)
    answers = (
        Answer.objects.filter(attempt=attempt)
        .select_related("question")
        .order_by("question__section", "question__question_number")
    )

    skill_label_map = {
        # ELA — SKILL_CHOICES keys
        "punctuation": "Punctuation",
        "usage_agreement": "Usage & Agreement",
        "sentence_structure": "Sentence Structure",
        "main_idea": "Main Idea",
        "supporting_detail": "Supporting Detail",
        "evidence_selection": "Evidence",
        "inference": "Inference",
        "vocabulary": "Vocabulary",
        "authors_craft": "Author's Craft",
        "cross_passage_synthesis": "Cross-passage",
        # Math — SKILL_CHOICES keys
        "number_operations": "Number Ops",
        "ratios_proportions": "Ratios & Proportions",
        "algebra": "Algebra",
        "geometry": "Geometry",
        "statistics_data": "Statistics",
        "probability": "Probability",
        "multistep_word_problems": "Multi-step",
        # Legacy keys
        "grammar_mechanics": "Grammar",
        "rhetoric_organization": "Rhetoric",
        "literal_comprehension": "Comprehension",
        "inference_analysis": "Inference",
        "algebraic_reasoning": "Algebra",
        "geometric_reasoning": "Geometry",
        "data_probability": "Statistics",
        "multistep_reasoning": "Multi-step",
        "fractions_decimals_percents": "Fractions & Percents",
        "functions_patterns": "Functions",
        "unknown": "Other",
    }

    total_answered = sum(1 for a in answers if a.selected_answer)
    total_correct = sum(1 for a in answers if a.is_correct)
    accuracy_pct = round(total_correct / total_answered * 100, 1) if total_answered else 0

    wrong_answers = [a for a in answers if a.selected_answer and not a.is_correct]

    # Wrong answers by skill
    skill_errors = {}
    for ans in wrong_answers:
        skill = ans.question.skill or "unknown"
        label = skill_label_map.get(skill, skill)
        skill_errors[label] = skill_errors.get(label, 0) + 1
    skill_errors_data = sorted(
        [{"label": k, "count": v} for k, v in skill_errors.items()],
        key=lambda x: x["count"], reverse=True
    )

    # Distractor trap analysis — build human-readable label map from DISTRACTOR_CHOICES
    from .forms import DISTRACTOR_CHOICES as _DC
    _dist_label = {}
    for entry in _DC:
        if isinstance(entry[1], (list, tuple)) and entry[0] not in ("", ):
            for key, label in entry[1]:
                _dist_label[key] = label
        elif entry[0]:
            _dist_label[entry[0]] = entry[1]

    import re as _re
    trap_counts = {}
    for ans in wrong_answers:
        trap = ans.question.distractor_types.get(ans.selected_answer, "")
        if trap:
            section = ans.question.section
            raw_label = _dist_label.get(trap, trap.replace("_", " ").title())
            # Strip leading section prefix like "(E) " or "(M) "
            clean_label = _re.sub(r"^\([EM]\)\s*", "", raw_label)
            key = (section, clean_label)
            trap_counts[key] = trap_counts.get(key, 0) + 1
    trap_data = sorted(
        [{"label": label, "section": section, "count": v} for (section, label), v in trap_counts.items()],
        key=lambda x: x["count"], reverse=True
    )

    # Difficulty breakdown of wrong answers
    diff_errors = {"easy": 0, "medium": 0, "hard": 0}
    diff_totals = {"easy": 0, "medium": 0, "hard": 0}
    for ans in answers:
        if ans.selected_answer:
            diff = ans.question.difficulty or "medium"
            if diff in diff_totals:
                diff_totals[diff] += 1
                if not ans.is_correct:
                    diff_errors[diff] += 1
    diff_breakdown = [
        {"label": "Easy", "errors": diff_errors["easy"], "total": diff_totals["easy"]},
        {"label": "Medium", "errors": diff_errors["medium"], "total": diff_totals["medium"]},
        {"label": "Hard", "errors": diff_errors["hard"], "total": diff_totals["hard"]},
    ]

    # Time vs accuracy scatter (only if timing data exists)
    scatter_data = []
    for ans in answers:
        if ans.selected_answer and ans.time_spent_seconds is not None:
            scatter_data.append({
                "x": ans.time_spent_seconds,
                "y": 1 if ans.is_correct else 0,
                "section": ans.question.section,
                "q": ans.question.question_number,
            })

    # Recommendations: top 3 weak skills
    skill_attempt = {}
    for ans in answers:
        if ans.selected_answer:
            skill = ans.question.skill or "unknown"
            if skill not in skill_attempt:
                skill_attempt[skill] = {"correct": 0, "total": 0}
            skill_attempt[skill]["total"] += 1
            if ans.is_correct:
                skill_attempt[skill]["correct"] += 1

    recommendations = []
    for skill, s in skill_attempt.items():
        if s["total"] == 0:
            continue
        pct = round(s["correct"] / s["total"] * 100, 1)
        recommendations.append({
            "label": skill_label_map.get(skill, skill),
            "skill": skill,
            "accuracy": pct,
            "wrong": s["total"] - s["correct"],
            "total": s["total"],
        })
    recommendations.sort(key=lambda x: x["accuracy"])
    recommendations = recommendations[:3]

    is_hunter = attempt.test.exam_type == "hunter"

    # Section time and accuracy summary — dynamic per exam type
    if is_hunter:
        _sections_ordered = [
            ("reading_comprehension", "Reading Comprehension"),
            ("quantitative_reasoning", "Quantitative Reasoning"),
            ("math_achievement", "Math Achievement"),
        ]
    else:
        _sections_ordered = [("ELA", "ELA"), ("Math", "Math")]

    section_summary_raw = {
        code: {"label": label, "correct": 0, "total": 0, "time_sum": 0, "has_time": False}
        for code, label in _sections_ordered
    }
    for ans in answers:
        sec = ans.question.section
        if sec not in section_summary_raw:
            continue
        if ans.selected_answer:
            section_summary_raw[sec]["total"] += 1
            if ans.is_correct:
                section_summary_raw[sec]["correct"] += 1
        if ans.time_spent_seconds is not None:
            section_summary_raw[sec]["time_sum"] += ans.time_spent_seconds
            section_summary_raw[sec]["has_time"] = True
    section_summary_data = []
    for code, _ in _sections_ordered:
        s = section_summary_raw[code]
        pct = round(s["correct"] / s["total"] * 100, 1) if s["total"] else 0
        section_summary_data.append({
            "section": s["label"],
            "section_code": code,
            "time_minutes": round(s["time_sum"] / 60, 1),
            "accuracy_pct": pct,
            "correct": s["correct"],
            "total": s["total"],
            "has_time": s["has_time"],
        })
    has_section_time = any(s["has_time"] for s in section_summary_data)

    # Passage accuracy breakdown (Hunter RC only)
    passage_summary = []
    if is_hunter:
        _passage_acc = {}
        for ans in answers:
            if ans.question.section != "reading_comprehension":
                continue
            pid = ans.question.passage_group_id or ""
            ptitle = ans.question.passage_title or pid
            if pid not in _passage_acc:
                _passage_acc[pid] = {"title": ptitle, "correct": 0, "total": 0}
            if ans.selected_answer:
                _passage_acc[pid]["total"] += 1
                if ans.is_correct:
                    _passage_acc[pid]["correct"] += 1
        passage_summary = [
            {
                "title": v["title"],
                "correct": v["correct"],
                "total": v["total"],
                "pct": round(v["correct"] / v["total"] * 100) if v["total"] else 0,
            }
            for v in _passage_acc.values() if v["total"] > 0
        ]

    # Full question review
    question_review = []
    for ans in answers:
        q = ans.question
        if q.question_type == "essay":
            continue
        choices_src = [("A", q.choice_a), ("B", q.choice_b), ("C", q.choice_c), ("D", q.choice_d)]
        if q.choice_e:
            choices_src.append(("E", q.choice_e))
        choices = []
        for letter, text in choices_src:
            if not text:
                continue
            status = "neutral"
            if letter == q.correct_answer:
                status = "correct"
            if letter == ans.selected_answer and not ans.is_correct:
                status = "wrong"
            choices.append({"letter": letter, "text": text, "status": status})
        distractor_type = ""
        if ans.selected_answer and not ans.is_correct and q.distractor_types:
            distractor_type = q.distractor_types.get(ans.selected_answer, "")
        skill_raw = q.skill or "unknown"
        skill_display = skill_label_map.get(skill_raw, skill_raw)
        question_review.append({
            "number": q.question_number,
            "section": q.section,
            "section_label": section_summary_raw.get(q.section, {}).get("label", q.section),
            "text": q.question_text,
            "choices": choices,
            "student_answer": ans.selected_answer or "",
            "correct_answer": q.correct_answer,
            "is_correct": ans.is_correct,
            "unanswered": not ans.selected_answer,
            "explanation": q.explanation or "",
            "skill": skill_display,
            "difficulty": (q.difficulty or "medium").capitalize(),
            "distractor_type": distractor_type,
            "is_grid_in": q.question_type == "grid_in",
            **_parse_quant_comparison(q.question_text),
        })

    # Parent insights: easy questions wrong, unanswered count, pacing
    easy_wrong = [q for q in question_review if q["difficulty"] == "Easy" and not q["is_correct"] and not q["unanswered"]]
    unanswered_count = sum(1 for q in question_review if q["unanswered"])
    total_time_minutes = sum(s["time_minutes"] for s in section_summary_data)
    pacing_ok = total_time_minutes <= 170 if has_section_time else None

    context = {
        "attempt": attempt,
        "is_hunter": is_hunter,
        "accuracy_pct": accuracy_pct,
        "total_correct": total_correct,
        "total_answered": total_answered,
        "skill_errors_data": skill_errors_data,
        "trap_data": trap_data,
        "diff_breakdown": diff_breakdown,
        "scatter_data": scatter_data,
        "has_timing": len(scatter_data) > 0,
        "recommendations": recommendations,
        "section_summary_data": section_summary_data,
        "has_section_time": has_section_time,
        "passage_summary": passage_summary,
        "question_review": question_review,
        "easy_wrong": easy_wrong,
        "unanswered_count": unanswered_count,
        "pacing_ok": pacing_ok,
        "total_time_minutes": round(total_time_minutes, 0) if has_section_time else None,
        "review_sections": [(s["section_code"], s["section"]) for s in section_summary_data],
        "parent_template": "shsat/base_hunter.html" if is_hunter else "shsat/base_shsat.html",
    }
    return render(request, "shsat/error_analysis.html", context)


@_require_shsat
def account(request):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    form = AccountForm(request.POST or None, instance=parent, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account updated.")
        return redirect("shsat_account")
    completed_attempts = (
        TestAttempt.objects.filter(parent=parent, is_completed=True)
        .select_related("test")
        .order_by("submitted_at")
    )
    return render(request, "shsat/account.html", {
        "form": form,
        "parent": parent,
        "completed_attempts": completed_attempts,
    })


@login_required(login_url="/shsat/login/")
@require_POST
def delete_attempt(request, attempt_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent)
    attempt.delete()
    messages.success(request, "Test attempt deleted.")
    return redirect("shsat_account")


# ---------------------------------------------------------------------------
# AJAX views
# ---------------------------------------------------------------------------

@login_required(login_url="/shsat/login/")
@require_POST
def save_answer(request):
    import json
    try:
        data = json.loads(request.body)
        attempt_id = data.get("attempt_id")
        question_id = data.get("question_id")
        selected = data.get("selected_answer", "").upper()
        time_spent = data.get("time_spent")

        parent, _ = Parent.objects.get_or_create(user=request.user)
        attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent, is_completed=False)
        answer, _ = Answer.objects.get_or_create(attempt=attempt, question_id=question_id)
        answer.selected_answer = selected
        update_fields = ["selected_answer"]
        if time_spent is not None:
            try:
                answer.time_spent_seconds = max(0, int(time_spent))
                update_fields.append("time_spent_seconds")
            except (TypeError, ValueError):
                pass
        answer.save(update_fields=update_fields)
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required(login_url="/shsat/login/")
@require_POST
def assign_modules(request):
    """
    Adaptive tests: score routing answers for a section, assign its module,
    add module question IDs to started_with, return question data for client.
    `section` param: 'ELA' or 'Math' (assigns one section at a time).
    """
    import json
    try:
        data = json.loads(request.body)
        attempt_id = data.get("attempt_id")
        section = data.get("section", "ELA")  # 'ELA' or 'Math'

        parent, _ = Parent.objects.get_or_create(user=request.user)
        attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent, is_completed=False)

        # Idempotent: if this section already assigned, return its current state
        if section == "ELA" and attempt.ela_module:
            return JsonResponse({"status": "already_assigned", "section": "ELA", "module": attempt.ela_module})
        if section == "Math" and attempt.math_module:
            return JsonResponse({"status": "already_assigned", "section": "Math", "module": attempt.math_module})

        # Score routing answers for this section only
        routing_answers = (
            Answer.objects.filter(attempt=attempt, question__stage='routing', question__section=section)
            .select_related('question')
        )
        r_correct = r_total = 0
        for a in routing_answers:
            r_total += 1
            if a.selected_answer and a.selected_answer.upper() == a.question.correct_answer.upper():
                r_correct += 1

        threshold = attempt.test.routing_threshold
        r_pct = r_correct / r_total if r_total else 0
        module = 'hard' if r_pct >= threshold else 'easy'
        stage = f'{module}_module'

        if section == "ELA":
            attempt.ela_module = module
        else:
            attempt.math_module = module

        # Fetch and add this section's module questions
        module_ids = list(
            attempt.test.questions.filter(section=section, stage=stage)
            .order_by('question_number').values_list('id', flat=True)
        )
        # Insert after the last routing question of this section (not at the end)
        # so that page reloads preserve the correct ELA→Math interleaving
        current_ids = list(attempt.started_with)
        routing_ids_for_section = set(
            attempt.test.questions.filter(stage='routing', section=section)
            .values_list('id', flat=True)
        )
        last_routing_pos = max(
            (i for i, qid in enumerate(current_ids) if qid in routing_ids_for_section),
            default=len(current_ids) - 1,
        )
        insert_at = last_routing_pos + 1
        attempt.started_with = current_ids[:insert_at] + module_ids + current_ids[insert_at:]
        attempt.save()

        for qid in module_ids:
            Answer.objects.get_or_create(attempt=attempt, question_id=qid)

        # Build question data (display_index continues after this section's routing count)
        module_qs = list(Question.objects.filter(id__in=module_ids).order_by('question_number'))
        ans_map = {
            a.question_id: a
            for a in Answer.objects.filter(attempt=attempt, question_id__in=module_ids)
        }
        q_data = []
        idx = r_total
        for q in module_qs:
            idx += 1
            ans = ans_map.get(q.id)
            q_data.append({
                "id": q.id,
                "section": q.section,
                "stage": q.stage,
                "is_routing": False,
                "question_number": q.question_number,
                "display_index": idx,
                "question_type": q.question_type,
                "use_efgh": attempt.test.exam_type == "shsat" and q.question_number % 2 == 0,
                "passage_group_id": q.passage_group_id or "",
                "passage_title": q.passage_title,
                "passage_text": q.passage_text,
                "image_url": q.image.url if q.image else "",
                "question_text": q.question_text,
                "choice_a": q.choice_a,
                "choice_b": q.choice_b,
                "choice_c": q.choice_c,
                "choice_d": q.choice_d,
                "selected": ans.selected_answer if ans else "",
                "is_flagged": ans.is_flagged if ans else False,
            })

        return JsonResponse({
            "status": "ok",
            "section": section,
            "module": module,
            "routing_correct": r_correct,
            "routing_total": r_total,
            "questions": q_data,
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required(login_url="/shsat/login/")
@require_POST
def flag_question(request):
    import json
    try:
        data = json.loads(request.body)
        attempt_id = data.get("attempt_id")
        question_id = data.get("question_id")
        flagged = data.get("flagged", False)

        parent, _ = Parent.objects.get_or_create(user=request.user)
        attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent, is_completed=False)
        answer, _ = Answer.objects.get_or_create(attempt=attempt, question_id=question_id)
        answer.is_flagged = flagged
        answer.save(update_fields=["is_flagged"])
        return JsonResponse({"status": "ok", "flagged": flagged})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required(login_url="/shsat/login/")
@require_POST
def report_question(request):
    import json
    try:
        data = json.loads(request.body)
        attempt_id = data.get("attempt_id")
        question_id = data.get("question_id")
        reason = (data.get("reason") or "").strip()

        parent, _ = Parent.objects.get_or_create(user=request.user)
        attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent)
        question = get_object_or_404(Question, id=question_id)

        QuestionReport.objects.create(
            question=question,
            attempt=attempt,
            parent=parent,
            reason=reason,
        )
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ---------------------------------------------------------------------------
# Content review interface (staff only)
# ---------------------------------------------------------------------------

STAGE_ORDER = {"easy_module": 0, "routing": 1, "hard_module": 2}
STAGE_LABELS = {
    "routing": "Routing",
    "easy_module": "Easy Module",
    "hard_module": "Hard Module",
    "standard": "Standard",
}
SKILL_LABELS = dict(Question.SKILL_CHOICES)

# Legacy skill values from old taxonomy — shown as-is if still in DB
SKILL_LABELS.update({
    "grammar_mechanics": "Grammar & Mechanics",
    "rhetoric_organization": "Rhetoric & Organization",
    "literal_comprehension": "Literal Comprehension",
    "inference_analysis": "Inference & Analysis",
    "algebraic_reasoning": "Algebraic Reasoning",
    "geometric_reasoning": "Geometric Reasoning",
    "data_probability": "Data & Probability",
    "multistep_reasoning": "Multi-step Reasoning",
    # Merged skills — still display if in DB
    "fractions_decimals_percents": "Fractions, Decimals & Percents",
    "functions_patterns": "Functions & Patterns",
})


@_staff_required
def content_test_add(request):
    if request.method == "POST":
        form = TestForm(request.POST)
        if form.is_valid():
            test = form.save()
            return redirect("shsat_content_test", test_id=test.id)
    else:
        form = TestForm()
    return render(request, "shsat/content_test_add.html", {"form": form})


@_staff_required
def content_test_edit(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == "POST":
        form = TestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            return redirect("shsat_content_test", test_id=test.id)
    else:
        form = TestForm(instance=test)
    return render(request, "shsat/content_test_add.html", {"form": form, "test": test})


HUNTER_SECTION_DISPLAY = [
    ("reading_comprehension", "Reading"),
    ("quantitative_reasoning", "Quant"),
    ("math_achievement", "Math Achievement"),
    ("writing", "Writing"),
]


@_staff_required
def content_home(request):
    tests = Test.objects.prefetch_related("questions").order_by("order", "id")
    test_data = []
    adaptive_stages = [("easy_module", "Easy"), ("routing", "Routing"), ("hard_module", "Hard")]
    standard_stages = [("routing", "Routing"), ("easy_module", "Easy"), ("hard_module", "Hard")]
    for test in tests:
        qs = test.questions.all()
        sections = {}
        if test.exam_type == "hunter":
            for section_code, section_label in HUNTER_SECTION_DISPLAY:
                sections[section_label] = [
                    ("standard", "Standard", qs.filter(section=section_code).count())
                ]
        else:
            stages = adaptive_stages if test.is_adaptive else standard_stages
            for section_code, section_label in [("ELA", "ELA"), ("Math", "Math")]:
                sections[section_label] = [
                    (key, label, qs.filter(section=section_code, stage=key).count())
                    for key, label in stages
                ]
        test_data.append({"test": test, "sections": sections})
    shsat_tests = [d for d in test_data if d["test"].exam_type == "shsat"]
    hunter_tests = [d for d in test_data if d["test"].exam_type == "hunter"]
    return render(request, "shsat/content_home.html", {
        "shsat_tests": shsat_tests,
        "hunter_tests": hunter_tests,
    })


@_staff_required
def content_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = test.questions.all().order_by("section", "stage", "question_number")

    def _group(section_code):
        # Collect questions per stage key
        groups = {}
        for q in questions:
            if q.section != section_code:
                continue
            groups.setdefault(q.stage, []).append(q)
        # For adaptive tests show routing/easy/hard; for standard show standard only
        if test.is_adaptive:
            stage_keys = ["easy_module", "routing", "hard_module"]
        else:
            stage_keys = ["standard"]
        # Always include any extra stages present in data
        for key in groups:
            if key not in stage_keys:
                stage_keys.append(key)
        return [
            (key, STAGE_LABELS.get(key, key), groups.get(key, []))
            for key in stage_keys
        ]

    if test.exam_type == "hunter":
        section_list = [
            (label, _group(code), code)
            for code, label in [
                ("reading_comprehension", "Reading Comprehension"),
                ("writing", "Writing"),
                ("quantitative_reasoning", "Quantitative Reasoning"),
                ("math_achievement", "Math Achievement"),
            ]
        ]
    else:
        section_list = [
            ("ELA", _group("ELA"), "ELA"),
            ("Math", _group("Math"), "Math"),
        ]

    # For Hunter tests, skills are human-readable strings not in SKILL_LABELS;
    # add any unknown skill values from this test mapped to themselves.
    skill_labels = dict(SKILL_LABELS)
    extra_skills = (
        test.questions.exclude(skill="")
        .exclude(skill__in=skill_labels.keys())
        .values_list("skill", flat=True)
        .distinct()
    )
    for s in extra_skills:
        skill_labels[s] = s

    context = {
        "test": test,
        "sections": section_list,
        "skill_labels": skill_labels,
    }
    return render(request, "shsat/content_test.html", context)


@_staff_required
def content_question_edit(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    if request.method == "POST":
        form = QuestionEditForm(request.POST, request.FILES, instance=question)
        if form.is_valid():
            form.save()
            next_id = request.POST.get("next_question_id")
            if next_id:
                return redirect("shsat_content_question_edit", question_id=next_id)
            return redirect("shsat_content_question_edit", question_id=question.id)
    else:
        form = QuestionEditForm(instance=question)

    # Find the next question in the same test using display order (easy → routing → hard)
    all_qs = list(
        Question.objects.filter(test_id=question.test_id)
        .order_by("section", "question_number")
        .values_list("id", "section", "stage", "question_number")
    )
    all_qs.sort(key=lambda q: (q[1], STAGE_ORDER.get(q[2], 99), q[3]))
    all_ids = [q[0] for q in all_qs]
    try:
        current_index = all_ids.index(question.id)
        next_question_id = all_ids[current_index + 1] if current_index + 1 < len(all_ids) else None
        prev_question_id = all_ids[current_index - 1] if current_index > 0 else None
    except ValueError:
        next_question_id = None
        prev_question_id = None

    skill_labels = dict(SKILL_LABELS)
    if question.skill and question.skill not in skill_labels:
        skill_labels[question.skill] = question.skill

    return render(request, "shsat/content_question_edit.html", {
        "question": question,
        "form": form,
        "skill_labels": skill_labels,
        "next_question_id": next_question_id,
        "prev_question_id": prev_question_id,
        "question_position": all_ids.index(question.id) + 1 if question.id in all_ids else None,
        "question_total": len(all_ids),
        "choices": [
            ("A", form["choice_a"], form["distractor_a"]),
            ("B", form["choice_b"], form["distractor_b"]),
            ("C", form["choice_c"], form["distractor_c"]),
            ("D", form["choice_d"], form["distractor_d"]),
            ("E", form["choice_e"], form["distractor_e"]),
        ],
    })


@_staff_required
def content_question_add(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    default_section = "reading_comprehension" if test.exam_type == "hunter" else "ELA"
    # Pre-fill section/stage from query params (passed from "Add question" button)
    initial = {
        "section": request.GET.get("section", default_section),
        "stage": request.GET.get("stage", "standard"),
    }
    if request.method == "POST":
        form = QuestionEditForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.test = test
            question.save()
            if request.POST.get("action") == "add_next":
                section = form.cleaned_data.get("section", default_section)
                stage = form.cleaned_data.get("stage", "standard")
                url = reverse("shsat_content_question_add", kwargs={"test_id": test_id})
                return redirect(f"{url}?section={section}&stage={stage}")
            return redirect("shsat_content_test", test_id=test_id)
    else:
        form = QuestionEditForm(initial=initial)
    return render(request, "shsat/content_question_add.html", {
        "test": test,
        "form": form,
        "skill_labels": SKILL_LABELS,
        "choices": [
            ("A", form["choice_a"], form["distractor_a"]),
            ("B", form["choice_b"], form["distractor_b"]),
            ("C", form["choice_c"], form["distractor_c"]),
            ("D", form["choice_d"], form["distractor_d"]),
            ("E", form["choice_e"], form["distractor_e"]),
        ],
    })


@_staff_required
@require_POST
def content_question_delete(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    test_id = question.test_id
    question.delete()
    return redirect("shsat_content_test", test_id=test_id)


@_staff_required
@require_POST
def content_test_delete(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    test.delete()
    messages.success(request, f"Test deleted.")
    return redirect("shsat_content_home")


@_staff_required
def content_test_export(request, test_id):
    import yaml
    test = get_object_or_404(Test, id=test_id)
    questions = test.questions.order_by("section", "stage", "question_number")

    records = []
    for q in questions:
        record = {
            "section": q.section,
            "stage": q.stage,
            "question_number": q.question_number,
            "question_type": q.question_type,
            "skill": q.skill,
            "difficulty": q.difficulty,
            "topic": q.topic,
            "passage_group_id": q.passage_group_id,
            "passage_title": q.passage_title,
            "passage_text": q.passage_text,
            "question_text": q.question_text,
            "choice_a": q.choice_a,
            "choice_b": q.choice_b,
            "choice_c": q.choice_c,
            "choice_d": q.choice_d,
            "choice_e": q.choice_e,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "distractor_types": q.distractor_types,
        }
        records.append(record)

    slug = test.title.lower().replace(" ", "_")
    filename = f"{slug}_export.yaml"
    content = yaml.dump(records, allow_unicode=True, sort_keys=False, default_flow_style=False)
    response = HttpResponse(content, content_type="text/yaml; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@_staff_required
def content_test_answers_csv(request, test_id):
    """Export all completed answers for a test as a CSV dataset for IRT analysis."""
    import csv as _csv
    test = get_object_or_404(Test, id=test_id)

    answers = (
        Answer.objects
        .filter(attempt__test=test, attempt__is_completed=True)
        .select_related("attempt", "attempt__parent", "question")
        .order_by("attempt_id", "question__section", "question__question_number")
    )

    slug = test.title.lower().replace(" ", "_")
    filename = f"{slug}_answers.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = _csv.writer(response)
    writer.writerow([
        "respondent_id", "attempt_id", "attempt_date",
        "section", "stage", "question_id", "question_number",
        "skill", "difficulty", "question_type",
        "selected_answer", "correct_answer", "is_correct",
        "time_spent_seconds",
    ])

    # Use a stable anonymised respondent ID (hash of parent pk)
    import hashlib
    def _anon(parent_id):
        return hashlib.sha256(f"shsat-{parent_id}".encode()).hexdigest()[:12]

    for ans in answers:
        q = ans.question
        writer.writerow([
            _anon(ans.attempt.parent_id),
            ans.attempt_id,
            ans.attempt.submitted_at.strftime("%Y-%m-%d") if ans.attempt.submitted_at else "",
            q.section,
            q.stage,
            q.id,
            q.question_number,
            q.skill,
            q.difficulty,
            q.question_type,
            ans.selected_answer or "",
            q.correct_answer,
            1 if ans.is_correct else 0,
            ans.time_spent_seconds if ans.time_spent_seconds is not None else "",
        ])

    return response
