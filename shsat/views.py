from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

from .models import Parent, Test, Question, TestAttempt, Answer, ManualScore, CutoffScore
from .forms import SignupForm, LoginForm, ManualScoreForm, NotesForm, AccountForm
from .scoring import scale_score, compute_placement


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
    cutoffs = CutoffScore.objects.all()

    # Build score history for Chart.js (combined platform + manual)
    from .scoring import scale_score as _scale
    score_history_raw = []
    for a in attempts:
        if a.composite_score is not None:
            score_history_raw.append({
                "_sort": a.submitted_at.date(),
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
            "_sort": m.date,
            "date": m.date.strftime("%b %d"),
            "composite": ela_scaled + math_scaled,
            "ela": ela_scaled,
            "math": math_scaled,
            "source": m.source_name,
        })
    score_history_raw.sort(key=lambda x: x["_sort"])
    score_history = [{k: v for k, v in e.items() if k != "_sort"} for e in score_history_raw]

    # Most recent composite = last entry in the date-sorted history (same source as chart)
    latest_composite = score_history_raw[-1]["composite"] if score_history_raw else None

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
        questions = list(test.questions.order_by("section", "question_number").values_list("id", flat=True))
        attempt = TestAttempt.objects.create(
            parent=parent,
            test=test,
            started_with=questions,
        )
        # Pre-create empty Answer rows
        for qid in questions:
            Answer.objects.get_or_create(attempt=attempt, question_id=qid)

    questions = Question.objects.filter(id__in=attempt.started_with).order_by("section", "question_number")
    answers_qs = Answer.objects.filter(attempt=attempt).select_related("question")
    answers_map = {a.question_id: a for a in answers_qs}

    # Build serializable question list for JSON rendering in JS
    q_list = []
    for q in questions:
        ans = answers_map.get(q.id)
        q_list.append({
            "id": q.id,
            "section": q.section,
            "question_number": q.question_number,
            "question_type": q.question_type,
            "use_efgh": q.question_number % 2 == 0,
            "passage_title": q.passage_title,
            "passage_text": q.passage_text,
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

    context = {
        "test": test,
        "attempt": attempt,
        "q_list": q_list,
        "remaining_seconds": remaining,
        "duration_seconds": settings.SHSAT_TEST_DURATION_SECONDS,
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
    ela_total = 0
    math_total = 0

    for ans in answers:
        q = ans.question
        if ans.selected_answer:
            correct = ans.selected_answer.upper() == q.correct_answer.upper()
            ans.is_correct = correct
            ans.save(update_fields=["is_correct"])
            if q.section == "ELA":
                ela_total += 1
                if correct:
                    ela_correct += 1
            else:
                math_total += 1
                if correct:
                    math_correct += 1

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
def account(request):
    parent, _ = Parent.objects.get_or_create(user=request.user)
    form = AccountForm(request.POST or None, instance=parent, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account updated.")
        return redirect("shsat_account")
    return render(request, "shsat/account.html", {"form": form, "parent": parent})


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

        parent, _ = Parent.objects.get_or_create(user=request.user)
        attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=parent, is_completed=False)
        answer, _ = Answer.objects.get_or_create(attempt=attempt, question_id=question_id)
        answer.selected_answer = selected
        answer.save(update_fields=["selected_answer"])
        return JsonResponse({"status": "ok"})
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
