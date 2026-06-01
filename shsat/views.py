from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

from .models import Parent, Test, Question, TestAttempt, Answer, ManualScore, CutoffScore
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


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def landing(request):
    if request.user.is_authenticated and hasattr(request.user, "shsat_profile"):
        return redirect("shsat_dashboard")
    return render(request, "shsat/landing.html")


def shsat_signup(request):
    if request.user.is_authenticated:
        return redirect("shsat_dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        Parent.objects.create(user=user)
        user = authenticate(request, email=user.email, password=form.cleaned_data["password1"])
        if user:
            login(request, user, backend="shsat.backends.EmailBackend")
        return redirect("shsat_dashboard")
    return render(request, "shsat/signup.html", {"form": form})


def shsat_login(request):
    if request.user.is_authenticated:
        return redirect("shsat_dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user, backend="shsat.backends.EmailBackend")
        return redirect(request.GET.get("next") or "shsat_dashboard")
    return render(request, "shsat/login.html", {"form": form})


def shsat_logout(request):
    logout(request)
    return redirect("shsat_landing")


def resources(request):
    return render(request, "shsat/resources.html")


# ---------------------------------------------------------------------------
# Protected views
# ---------------------------------------------------------------------------

@login_required(login_url="/shsat/login/")
def dashboard(request):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    attempts = (
        TestAttempt.objects.filter(parent=parent, is_completed=True)
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
    for i, entry in enumerate(other_entries):
        entry["seq"] = f"Test {i + 1}"
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
        for a in attempts
        if a.composite_score is not None
    ]

    # Skill & difficulty accuracy aggregation (across all completed attempts)
    all_answers = Answer.objects.filter(
        attempt__parent=parent,
        attempt__is_completed=True,
        is_correct__isnull=False,
    ).select_related("question")

    skill_stats = {}   # skill -> {correct, total, time_sum, time_count}
    diff_stats = {}  # no longer used for charts

    for ans in all_answers:
        skill = ans.question.skill or "unknown"
        diff = ans.question.difficulty or "medium"

        if skill not in skill_stats:
            skill_stats[skill] = {"correct": 0, "total": 0, "time_sum": 0, "time_count": 0}
        skill_stats[skill]["total"] += 1
        if ans.is_correct:
            skill_stats[skill]["correct"] += 1
        if ans.time_spent_seconds is not None:
            skill_stats[skill]["time_sum"] += ans.time_spent_seconds
            skill_stats[skill]["time_count"] += 1


    # Sort skills by accuracy ascending (weakest first)
    skill_label_map = dict(Question.SKILL_CHOICES)
    skill_label_map.update({
        "grammar_mechanics": "Grammar & Mechanics",
        "rhetoric_organization": "Rhetoric & Organization",
        "literal_comprehension": "Literal Comprehension",
        "inference_analysis": "Inference & Analysis",
        "algebraic_reasoning": "Algebraic Reasoning",
        "geometric_reasoning": "Geometric Reasoning",
        "data_probability": "Data & Probability",
        "multistep_reasoning": "Multi-step Reasoning",
        "fractions_decimals_percents": "Fractions, Decimals & Percents",
        "functions_patterns": "Functions & Patterns",
        "unknown": "Uncategorized",
    })

    skill_accuracy_data = []
    for skill, s in skill_stats.items():
        if s["total"] == 0:
            continue
        pct = round(s["correct"] / s["total"] * 100, 1)
        avg_time = round(s["time_sum"] / s["time_count"] / 60, 2) if s["time_count"] > 0 else None
        skill_accuracy_data.append({
            "skill": skill,
            "label": skill_label_map.get(skill, skill),
            "accuracy": pct,
            "correct": s["correct"],
            "total": s["total"],
            "avg_time": avg_time,
        })
    skill_accuracy_data.sort(key=lambda x: x["accuracy"])

    weakest_skill = skill_accuracy_data[0]["label"] if skill_accuracy_data else None

    # Avg time per question across all timed answers
    timed_answers = [a for a in all_answers if a.time_spent_seconds is not None]
    has_timing_data = len(timed_answers) > 0
    avg_time_per_q = (
        round(sum(a.time_spent_seconds for a in timed_answers) / len(timed_answers) / 60, 1)
        if timed_answers else None
    )

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
        return redirect("shsat_dashboard")
    return render(request, "shsat/log_score.html", {"form": form})


@login_required(login_url="/shsat/login/")
def test_list(request):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    tests = Test.objects.filter(is_published=True)
    completed_ids = set(
        TestAttempt.objects.filter(parent=parent, is_completed=True).values_list("test_id", flat=True)
    )
    free_limit = settings.SHSAT_FREE_TEST_LIMIT
    tests_taken = TestAttempt.objects.filter(parent=parent, is_completed=True).count()
    context = {
        "tests": tests,
        "completed_ids": completed_ids,
        "free_limit": free_limit,
        "tests_taken": tests_taken,
    }
    return render(request, "shsat/test_list.html", context)


@login_required(login_url="/shsat/login/")
def test_intro(request, test_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    test = get_object_or_404(Test, id=test_id, is_published=True)
    # Check if there's an in-progress attempt
    in_progress = TestAttempt.objects.filter(parent=parent, test=test, is_completed=False).first()
    context = {
        "test": test,
        "in_progress": in_progress,
        "ela_count": test.ela_questions().count(),
        "math_count": test.math_questions().count(),
        "duration_hours": settings.SHSAT_TEST_DURATION_SECONDS // 3600,
    }
    return render(request, "shsat/test_intro.html", context)


@login_required(login_url="/shsat/login/")
def test_take(request, test_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    test = get_object_or_404(Test, id=test_id, is_published=True)

    # Get or create attempt
    attempt = TestAttempt.objects.filter(parent=parent, test=test, is_completed=False).first()
    if not attempt:
        if test.is_adaptive:
            # Adaptive: start with routing questions only; modules assigned later
            question_ids = list(
                test.questions.filter(stage='routing')
                .order_by('section', 'question_number')
                .values_list('id', flat=True)
            )
        else:
            question_ids = list(
                test.questions.order_by('section', 'question_number')
                .values_list('id', flat=True)
            )
        attempt = TestAttempt.objects.create(
            parent=parent,
            test=test,
            started_with=question_ids,
        )
        for qid in question_ids:
            Answer.objects.get_or_create(attempt=attempt, question_id=qid)

    from django.db.models import Case, When, IntegerField, Value
    stage_sort = Case(
        When(stage='routing', then=Value(0)),
        When(stage='easy_module', then=Value(1)),
        When(stage='hard_module', then=Value(2)),
        default=Value(3),
        output_field=IntegerField()
    )
    questions = (
        Question.objects.filter(id__in=attempt.started_with)
        .annotate(stage_sort=stage_sort)
        .order_by("section", "stage_sort", "question_number")
    )
    answers_qs = Answer.objects.filter(attempt=attempt).select_related("question")
    answers_map = {a.question_id: a for a in answers_qs}

    # Build serializable question list for JSON rendering in JS
    # Track per-section display index (1-based sequential)
    section_counters = {"ELA": 0, "Math": 0}
    q_list = []
    for q in questions:
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
            "use_efgh": q.question_number % 2 == 0,
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

    elapsed = int((timezone.now() - attempt.started_at).total_seconds())
    remaining = max(0, settings.SHSAT_TEST_DURATION_SECONDS - elapsed)

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
    return render(request, "shsat/test_take.html", context)


@login_required(login_url="/shsat/login/")
@require_POST
def test_submit(request, test_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    attempt = get_object_or_404(TestAttempt, test_id=test_id, parent=parent, is_completed=False)

    answers = Answer.objects.filter(attempt=attempt).select_related("question")
    ela_correct = 0
    math_correct = 0

    for ans in answers:
        q = ans.question
        if ans.selected_answer:
            correct = ans.selected_answer.upper() == q.correct_answer.upper()
            ans.is_correct = correct
            ans.save(update_fields=["is_correct"])
            if q.section == "ELA":
                if correct:
                    ela_correct += 1
            else:
                if correct:
                    math_correct += 1

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

    return redirect("shsat_test_results", attempt_id=attempt.id)


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
    if request.method == "POST" and notes_form.is_valid():
        attempt.notes = notes_form.cleaned_data["notes"]
        attempt.save(update_fields=["notes"])
        return redirect("shsat_test_results", attempt_id=attempt.id)

    ela_answers = [a for a in answers if a.question.section == "ELA"]
    math_answers = [a for a in answers if a.question.section == "Math"]

    context = {
        "attempt": attempt,
        "ela_answers": ela_answers,
        "math_answers": math_answers,
        "placement_data": placement_data,
        "notes_form": notes_form,
    }
    return render(request, "shsat/test_results.html", context)


@login_required(login_url="/shsat/login/")
def error_analysis(request, attempt_id):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent, is_completed=True)
    answers = (
        Answer.objects.filter(attempt=attempt)
        .select_related("question")
        .order_by("question__section", "question__question_number")
    )

    skill_label_map = dict(Question.SKILL_CHOICES)
    skill_label_map.update({
        "grammar_mechanics": "Grammar & Mechanics",
        "rhetoric_organization": "Rhetoric & Organization",
        "literal_comprehension": "Literal Comprehension",
        "inference_analysis": "Inference & Analysis",
        "algebraic_reasoning": "Algebraic Reasoning",
        "geometric_reasoning": "Geometric Reasoning",
        "data_probability": "Data & Probability",
        "multistep_reasoning": "Multi-step Reasoning",
        "unknown": "Uncategorized",
    })

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

    # Distractor trap analysis
    trap_counts = {}
    for ans in wrong_answers:
        trap = ans.question.distractor_types.get(ans.selected_answer, "")
        if trap:
            section = ans.question.section
            key = f"{section}: {trap}"
            trap_counts[key] = trap_counts.get(key, 0) + 1
    trap_data = sorted(
        [{"label": k, "count": v} for k, v in trap_counts.items()],
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

    # Section time and accuracy summary
    section_summary_raw = {
        "ELA":  {"correct": 0, "total": 0, "time_sum": 0, "has_time": False},
        "Math": {"correct": 0, "total": 0, "time_sum": 0, "has_time": False},
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
    for sec in ["ELA", "Math"]:
        s = section_summary_raw[sec]
        pct = round(s["correct"] / s["total"] * 100, 1) if s["total"] else 0
        section_summary_data.append({
            "section": sec,
            "time_minutes": round(s["time_sum"] / 60, 1),
            "accuracy_pct": pct,
            "correct": s["correct"],
            "total": s["total"],
            "has_time": s["has_time"],
        })
    has_section_time = any(s["has_time"] for s in section_summary_data)

    # Full question review (for parent)
    question_review = []
    for ans in answers:
        q = ans.question
        choices = []
        for letter, text in [("A", q.choice_a), ("B", q.choice_b), ("C", q.choice_c), ("D", q.choice_d)]:
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
        question_review.append({
            "number": q.question_number,
            "section": q.section,
            "text": q.question_text,
            "choices": choices,
            "student_answer": ans.selected_answer or "",
            "correct_answer": q.correct_answer,
            "is_correct": ans.is_correct,
            "unanswered": not ans.selected_answer,
            "explanation": q.explanation or "",
            "skill": skill_label_map.get(q.skill or "unknown", q.skill or "Unknown"),
            "difficulty": (q.difficulty or "medium").capitalize(),
            "distractor_type": distractor_type,
            "is_grid_in": q.question_type == "grid_in",
        })

    # Parent insights: easy questions wrong, unanswered count, pacing
    easy_wrong = [q for q in question_review if q["difficulty"] == "Easy" and not q["is_correct"] and not q["unanswered"]]
    unanswered_count = sum(1 for q in question_review if q["unanswered"])
    total_time_minutes = sum(s["time_minutes"] for s in section_summary_data)
    pacing_ok = total_time_minutes <= 170 if has_section_time else None  # 3h test = 180m, flag if >170m

    context = {
        "attempt": attempt,
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
        "question_review": question_review,
        "easy_wrong": easy_wrong,
        "unanswered_count": unanswered_count,
        "pacing_ok": pacing_ok,
        "total_time_minutes": round(total_time_minutes, 0) if has_section_time else None,
        "review_sections": ["ELA", "Math"],
    }
    return render(request, "shsat/error_analysis.html", context)


@login_required(login_url="/shsat/login/")
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
        attempt.started_with = list(attempt.started_with) + module_ids
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
                "use_efgh": q.question_number % 2 == 0,
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


@_staff_required
def content_home(request):
    tests = Test.objects.prefetch_related("questions").order_by("order", "id")
    test_data = []
    adaptive_stages = [("easy_module", "Easy"), ("routing", "Routing"), ("hard_module", "Hard")]
    standard_stages = [("routing", "Routing"), ("easy_module", "Easy"), ("hard_module", "Hard")]
    for test in tests:
        qs = test.questions.all()
        stages = adaptive_stages if test.is_adaptive else standard_stages
        sections = {}
        for section_code, section_label in [("ELA", "ELA"), ("Math", "Math")]:
            sections[section_label] = [
                (key, label, qs.filter(section=section_code, stage=key).count())
                for key, label in stages
            ]
        test_data.append({"test": test, "sections": sections})
    return render(request, "shsat/content_home.html", {"test_data": test_data})


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

    context = {
        "test": test,
        "sections": [
            ("ELA", _group("ELA"), "ELA"),
            ("Math", _group("Math"), "Math"),
        ],
        "skill_labels": SKILL_LABELS,
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

    return render(request, "shsat/content_question_edit.html", {
        "question": question,
        "form": form,
        "skill_labels": SKILL_LABELS,
        "next_question_id": next_question_id,
        "prev_question_id": prev_question_id,
        "question_position": all_ids.index(question.id) + 1 if question.id in all_ids else None,
        "question_total": len(all_ids),
        "choices": [
            ("A", form["choice_a"], form["distractor_a"]),
            ("B", form["choice_b"], form["distractor_b"]),
            ("C", form["choice_c"], form["distractor_c"]),
            ("D", form["choice_d"], form["distractor_d"]),
        ],
    })


@_staff_required
def content_question_add(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    # Pre-fill section/stage from query params (passed from "Add question" button)
    initial = {
        "section": request.GET.get("section", "ELA"),
        "stage": request.GET.get("stage", "standard"),
    }
    if request.method == "POST":
        form = QuestionEditForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.test = test
            question.save()
            # Also persist distractor_types from the form
            dt = {}
            for letter, field in [("A", "distractor_a"), ("B", "distractor_b"),
                                   ("C", "distractor_c"), ("D", "distractor_d")]:
                val = form.cleaned_data.get(field, "")
                if val:
                    dt[letter] = val
            question.distractor_types = dt
            question.save(update_fields=["distractor_types"])
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
