from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Count, Q, Avg, Max
from django.utils import timezone

from .models import (
    Tutor, TutorStudent, Parent, Test, TestAttempt, Answer,
    ManualScore, CutoffScore,
)
from .forms import TutorSignupForm, TutorAccountForm, LoginForm
from .scoring import scale_score, compute_placement


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def _tutor_required(view_func):
    """Only allow users with a tutor_profile. Staff bypass."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/tutor/login/?next={request.path}")
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        try:
            request.user.tutor_profile
        except Tutor.DoesNotExist:
            return redirect("tutor_login")
        return view_func(request, *args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _send_tutor_verification_email(request, user, tutor):
    verify_url = request.build_absolute_uri(f"/tutor/verify-email/{tutor.email_verification_token}/")
    body = render_to_string("shsat/tutor_verify_email.html", {"verify_url": verify_url})
    send_mail(
        subject="Verify your email — Tutor Portal",
        message=f"Verify your email: {verify_url}",
        from_email=None,
        recipient_list=[user.email],
        html_message=body,
        fail_silently=True,
    )


def tutor_landing(request):
    if request.method == "POST":
        # Honeypot
        if request.POST.get("website"):
            return redirect("/tutor/?sent=1")

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
            from pages.models import ContactMessage
            ContactMessage.objects.create(name=name, email=email, message=message, source="tutor")
            try:
                send_mail(
                    subject=f"New tutor inquiry from {name}",
                    message=f"From: {name} <{email}>\nSource: tutor landing\n\n{message}",
                    from_email=None,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass
            return redirect("/tutor/?sent=1")
        return render(request, "shsat/tutor_landing.html", {
            "errors": errors,
            "form": {"name": name, "email": email, "message": message},
        })

    sent = request.GET.get("sent") == "1"
    return render(request, "shsat/tutor_landing.html", {"sent": sent})


def tutor_signup(request):
    if request.user.is_authenticated:
        try:
            request.user.tutor_profile
            return redirect("tutor_dashboard")
        except Tutor.DoesNotExist:
            pass
    form = TutorSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        tutor = Tutor.objects.create(
            user=user,
            business_name=form.cleaned_data.get("business_name", ""),
            email_verified=False,
        )
        _send_tutor_verification_email(request, user, tutor)
        user = authenticate(request, email=user.email, password=form.cleaned_data["password1"])
        if user:
            login(request, user, backend="shsat.backends.EmailBackend")
        return redirect("tutor_verify_pending")
    return render(request, "shsat/tutor_signup.html", {"form": form})


def tutor_login(request):
    if request.user.is_authenticated:
        try:
            request.user.tutor_profile
            return redirect("tutor_dashboard")
        except Tutor.DoesNotExist:
            pass
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        try:
            user.tutor_profile
        except Tutor.DoesNotExist:
            form.add_error(None, "This account is not a tutor account.")
            return render(request, "shsat/tutor_login.html", {"form": form})
        login(request, user, backend="shsat.backends.EmailBackend")
        return redirect(request.GET.get("next") or "tutor_dashboard")
    return render(request, "shsat/tutor_login.html", {"form": form})


def tutor_logout(request):
    logout(request)
    return redirect("tutor_landing")


@login_required(login_url="/tutor/login/")
def tutor_verify_pending(request):
    try:
        tutor = request.user.tutor_profile
        if tutor.email_verified:
            return redirect("tutor_dashboard")
    except Tutor.DoesNotExist:
        pass
    resent = request.GET.get("resent") == "1"
    return render(request, "shsat/tutor_verify_pending.html", {
        "email": request.user.email,
        "resent": resent,
    })


@login_required(login_url="/tutor/login/")
@require_POST
def tutor_verify_resend(request):
    try:
        tutor = request.user.tutor_profile
        if not tutor.email_verified:
            _send_tutor_verification_email(request, request.user, tutor)
    except Tutor.DoesNotExist:
        pass
    return redirect("/tutor/verify-email/?resent=1")


def tutor_verify_email(request, token):
    tutor = get_object_or_404(Tutor, email_verification_token=token)
    tutor.email_verified = True
    tutor.save(update_fields=["email_verified"])
    if not request.user.is_authenticated:
        login(request, tutor.user, backend="shsat.backends.EmailBackend")
    return redirect("tutor_dashboard")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def _get_student_display_name(ts):
    """Return a display name for a TutorStudent link."""
    if ts.nickname:
        return ts.nickname
    if ts.parent.child_nickname:
        return ts.parent.child_nickname
    return ts.parent.user.first_name or ts.parent.user.email.split("@")[0]


@_tutor_required
def tutor_dashboard(request, exam_type="shsat"):
    tutor = request.user.tutor_profile
    is_hunter = exam_type == "hunter"
    links = (
        TutorStudent.objects
        .filter(tutor=tutor)
        .select_related("parent__user")
        .order_by("added_at")
    )

    # Build student roster data
    students = []
    all_correct = 0
    all_total_answered = 0
    total_tests = 0

    # For Hunter percentage scoring, preload question counts
    if is_hunter:
        from .models import Question as _Question
        _all_test_ids = set(
            TestAttempt.objects.filter(
                parent_id__in=[ts.parent_id for ts in links],
                is_completed=True, test__is_drill=False, test__exam_type="hunter",
            ).values_list("test_id", flat=True)
        )
        q_counts = {}
        for _row in (
            _Question.objects.filter(test_id__in=_all_test_ids)
            .values("test_id", "section")
            .annotate(n=Count("id"))
        ):
            q_counts.setdefault(_row["test_id"], {})[_row["section"]] = _row["n"]

    for ts in links:
        parent = ts.parent
        attempts = (
            TestAttempt.objects
            .filter(parent=parent, is_completed=True, test__is_drill=False, test__exam_type=exam_type)
            .select_related("test")
            .order_by("-submitted_at")
        )
        latest = attempts.first()
        test_count = attempts.count()
        total_tests += test_count

        # Accuracy across all answers for this exam type
        ans_stats = (
            Answer.objects
            .filter(
                attempt__parent=parent,
                attempt__is_completed=True,
                attempt__test__is_drill=False,
                attempt__test__exam_type=exam_type,
                is_correct__isnull=False,
            )
            .aggregate(
                correct=Count("id", filter=Q(is_correct=True)),
                total=Count("id"),
            )
        )
        all_correct += ans_stats["correct"] or 0
        all_total_answered += ans_stats["total"] or 0

        student_data = {
            "ts": ts,
            "parent": parent,
            "name": _get_student_display_name(ts),
            "grade": parent.child_grade,
            "test_count": test_count,
            "last_active": latest.submitted_at if latest else None,
        }

        if is_hunter and latest and latest.composite_score is not None:
            tc = q_counts.get(latest.test_id, {})
            rc_total = tc.get("reading_comprehension", 0)
            math_total = tc.get("quantitative_reasoning", 0) + tc.get("math_achievement", 0)
            comp_total = rc_total + math_total
            student_data["latest_pct"] = round(latest.composite_score / comp_total * 100) if comp_total else None
            student_data["latest_rc_pct"] = round(latest.ela_correct / rc_total * 100) if rc_total and latest.ela_correct is not None else None
            student_data["latest_math_pct"] = round(latest.math_correct / math_total * 100) if math_total and latest.math_correct is not None else None
        elif not is_hunter:
            student_data["latest_composite"] = latest.composite_score if latest else None
            student_data["latest_ela"] = latest.ela_scaled if latest else None
            student_data["latest_math"] = latest.math_scaled if latest else None

        students.append(student_data)

    # Stat cards
    active_students = len(students)
    if is_hunter:
        pcts = [s["latest_pct"] for s in students if s.get("latest_pct")]
        class_avg = round(sum(pcts) / len(pcts)) if pcts else None
    else:
        composites = [s["latest_composite"] for s in students if s.get("latest_composite")]
        class_avg = round(sum(composites) / len(composites)) if composites else None
    avg_accuracy = round(all_correct / all_total_answered * 100, 1) if all_total_answered else None

    # Class-wide skill weakness heatmap
    skill_label_map = {
        "punctuation": "Punctuation", "usage_agreement": "Usage & Agreement",
        "sentence_structure": "Sentence Structure", "main_idea": "Main Idea",
        "supporting_detail": "Supporting Detail", "evidence_selection": "Evidence",
        "inference": "Inference", "vocabulary": "Vocabulary",
        "authors_craft": "Author's Craft", "cross_passage_synthesis": "Cross-passage",
        "number_operations": "Number Ops", "ratios_proportions": "Ratios & Proportions",
        "algebra": "Algebra", "geometry": "Geometry",
        "statistics_data": "Statistics", "probability": "Probability",
        "multistep_word_problems": "Multi-step",
    }

    parent_ids = [ts.parent_id for ts in links]
    all_answers = (
        Answer.objects
        .filter(
            attempt__parent_id__in=parent_ids,
            attempt__is_completed=True,
            attempt__test__is_drill=False,
            attempt__test__exam_type=exam_type,
            is_correct__isnull=False,
        )
        .select_related("question")
    )

    skill_stats = {}
    for ans in all_answers:
        skill = ans.question.skill or "unknown"
        section = ans.question.section or "unknown"
        if skill not in skill_label_map:
            continue
        if skill not in skill_stats:
            skill_stats[skill] = {"correct": 0, "total": 0, "section": section}
        skill_stats[skill]["total"] += 1
        if ans.is_correct:
            skill_stats[skill]["correct"] += 1

    skill_accuracy_data = []
    for skill, s in skill_stats.items():
        if s["total"] == 0:
            continue
        pct = round(s["correct"] / s["total"] * 100, 1)
        skill_accuracy_data.append({
            "skill": skill,
            "label": skill_label_map[skill],
            "section": s["section"],
            "accuracy": pct,
            "correct": s["correct"],
            "total": s["total"],
        })
    skill_accuracy_data.sort(key=lambda x: x["accuracy"])

    # Per-student score history for class progress chart
    import json
    student_histories = []
    for s in students:
        parent = s["parent"]
        attempts = (
            TestAttempt.objects
            .filter(parent=parent, is_completed=True, test__is_drill=False, test__exam_type=exam_type)
            .select_related("test")
            .order_by("submitted_at")
        )
        scores = []
        for a in attempts:
            if is_hunter:
                tc = q_counts.get(a.test_id, {})
                comp_total = sum(tc.values())
                val = round(a.composite_score / comp_total * 100) if comp_total and a.composite_score else None
            else:
                val = a.composite_score
            if val is not None:
                scores.append({
                    "label": a.test.title if a.test else f"Test",
                    "date": a.submitted_at.strftime("%b %d"),
                    "score": val,
                })
        if scores:
            student_histories.append({
                "name": s["name"],
                "scores": scores,
            })
    student_histories_json = json.dumps(student_histories)

    context = {
        "tutor": tutor,
        "students": students,
        "active_students": active_students,
        "class_avg": class_avg,
        "total_tests": total_tests,
        "avg_accuracy": avg_accuracy,
        "skill_accuracy_data": skill_accuracy_data,
        "student_histories_json": student_histories_json,
        "exam_type": exam_type,
        "is_hunter": is_hunter,
        "active_tab": exam_type,
    }
    return render(request, "shsat/tutor_dashboard.html", context)


# ---------------------------------------------------------------------------
# Student detail — reuse dashboard context
# ---------------------------------------------------------------------------

def _compute_dashboard_context(parent):
    """Compute the dashboard data for a given parent. Shared by parent and tutor views."""
    from collections import defaultdict
    from .scoring import scale_score as _scale
    import math as _math

    attempts = (
        TestAttempt.objects.filter(parent=parent, is_completed=True, test__is_drill=False, test__exam_type="shsat")
        .select_related("test")
        .order_by("-submitted_at")
    )
    manual_scores = ManualScore.objects.filter(parent=parent).order_by("-date")
    latest_year = CutoffScore.objects.aggregate(Max("admissions_year"))["admissions_year__max"]
    cutoffs = CutoffScore.objects.filter(admissions_year=latest_year).order_by("cutoff_score")

    # Score history
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

    baseline_entries = [e for e in score_history_raw if "baseline" in e["source"].lower()]
    other_entries = [e for e in score_history_raw if "baseline" not in e["source"].lower()]
    collapsed = []
    if baseline_entries:
        best = baseline_entries[-1]
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

    latest_attempt = attempts.filter(composite_score__isnull=False).first()
    latest_composite = latest_attempt.composite_score if latest_attempt else None
    placement_data = compute_placement(latest_composite, cutoffs) if latest_composite else []

    cutoffs_list = [{"school_short": c.school_short, "cutoff": c.cutoff_score} for c in cutoffs]
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

    # Skill accuracy
    all_answers = Answer.objects.filter(
        attempt__parent=parent,
        attempt__is_completed=True,
        attempt__test__is_drill=False,
        is_correct__isnull=False,
    ).select_related("question")

    skill_label_map = {
        "punctuation": "Punctuation", "usage_agreement": "Usage & Agreement",
        "sentence_structure": "Sentence Structure", "main_idea": "Main Idea",
        "supporting_detail": "Supporting Detail", "evidence_selection": "Evidence",
        "inference": "Inference", "vocabulary": "Vocabulary",
        "authors_craft": "Author's Craft", "cross_passage_synthesis": "Cross-passage",
        "number_operations": "Number Ops", "ratios_proportions": "Ratios & Proportions",
        "algebra": "Algebra", "geometry": "Geometry",
        "statistics_data": "Statistics", "probability": "Probability",
        "multistep_word_problems": "Multi-step",
        "grammar_mechanics": "Grammar", "rhetoric_organization": "Rhetoric",
        "literal_comprehension": "Comprehension", "inference_analysis": "Inference",
        "algebraic_reasoning": "Algebra", "geometric_reasoning": "Geometry",
        "data_probability": "Statistics", "multistep_reasoning": "Multi-step",
        "fractions_decimals_percents": "Fractions & Percents",
        "functions_patterns": "Functions", "unknown": "Other",
    }

    skill_stats = {}
    att_skill_correct = defaultdict(lambda: defaultdict(int))
    att_skill_total = defaultdict(lambda: defaultdict(int))

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

    skill_weak_counts = defaultdict(int)
    for att_id, totals in att_skill_total.items():
        for skill, total in totals.items():
            if total >= 2:
                correct = att_skill_correct[att_id].get(skill, 0)
                if correct / total < 0.70:
                    skill_weak_counts[skill] += 1

    skill_accuracy_data = []
    for skill, s in skill_stats.items():
        if s["total"] == 0:
            continue
        if skill not in skill_label_map:
            continue
        raw_label = skill_label_map[skill]
        label = raw_label.replace("_", " ").title() if "_" in raw_label else raw_label
        pct = round(s["correct"] / s["total"] * 100, 1)
        avg_time = round(s["time_sum"] / s["time_count"] / 60, 2) if s["time_count"] > 0 else None
        skill_accuracy_data.append({
            "skill": skill, "label": label, "section": s["section"],
            "accuracy": pct, "correct": s["correct"], "total": s["total"],
            "avg_time": avg_time,
        })
    skill_accuracy_data.sort(key=lambda x: x["accuracy"])

    for s in skill_accuracy_data:
        weak_count = skill_weak_counts.get(s["skill"], 0)
        s["weak_attempts"] = weak_count
        s["is_persistent"] = weak_count >= 2

    weakest_skill = skill_accuracy_data[0]["label"] if skill_accuracy_data else None

    timed_answers = [a for a in all_answers if a.time_spent_seconds is not None]
    has_timing_data = len(timed_answers) > 0
    avg_time_per_q = (
        round(sum(a.time_spent_seconds for a in timed_answers) / len(timed_answers) / 60, 1)
        if timed_answers else None
    )

    all_platform_scores = list(
        TestAttempt.objects.filter(
            is_completed=True, composite_score__isnull=False,
            test__is_drill=False, test__exam_type="shsat"
        ).values_list("composite_score", flat=True)
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

    return {
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


def _compute_error_analysis_context(attempt):
    """Compute error analysis data for an attempt. Shared by parent and tutor views."""
    import re as _re

    answers = (
        Answer.objects.filter(attempt=attempt)
        .select_related("question")
        .order_by("question__section", "question__question_number")
    )

    skill_label_map = {
        "punctuation": "Punctuation", "usage_agreement": "Usage & Agreement",
        "sentence_structure": "Sentence Structure", "main_idea": "Main Idea",
        "supporting_detail": "Supporting Detail", "evidence_selection": "Evidence",
        "inference": "Inference", "vocabulary": "Vocabulary",
        "authors_craft": "Author's Craft", "cross_passage_synthesis": "Cross-passage",
        "number_operations": "Number Ops", "ratios_proportions": "Ratios & Proportions",
        "algebra": "Algebra", "geometry": "Geometry",
        "statistics_data": "Statistics", "probability": "Probability",
        "multistep_word_problems": "Multi-step",
        "grammar_mechanics": "Grammar", "rhetoric_organization": "Rhetoric",
        "literal_comprehension": "Comprehension", "inference_analysis": "Inference",
        "algebraic_reasoning": "Algebra", "geometric_reasoning": "Geometry",
        "data_probability": "Statistics", "multistep_reasoning": "Multi-step",
        "fractions_decimals_percents": "Fractions & Percents",
        "functions_patterns": "Functions", "unknown": "Other",
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

    # Distractor trap analysis
    from .forms import DISTRACTOR_CHOICES as _DC
    _dist_label = {}
    for entry in _DC:
        if isinstance(entry[1], (list, tuple)) and entry[0] not in ("",):
            for key, label in entry[1]:
                _dist_label[key] = label
        elif entry[0]:
            _dist_label[entry[0]] = entry[1]

    trap_counts = {}
    for ans in wrong_answers:
        trap = ans.question.distractor_types.get(ans.selected_answer, "")
        if trap:
            section = ans.question.section
            raw_label = _dist_label.get(trap, trap.replace("_", " ").title())
            clean_label = _re.sub(r"^\([EM]\)\s*", "", raw_label)
            key = (section, clean_label)
            trap_counts[key] = trap_counts.get(key, 0) + 1
    trap_data = sorted(
        [{"label": label, "section": section, "count": v} for (section, label), v in trap_counts.items()],
        key=lambda x: x["count"], reverse=True
    )

    # Difficulty breakdown
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

    # Time vs accuracy scatter
    scatter_data = []
    for ans in answers:
        if ans.selected_answer and ans.time_spent_seconds is not None:
            scatter_data.append({
                "x": ans.time_spent_seconds,
                "y": 1 if ans.is_correct else 0,
                "section": ans.question.section,
                "q": ans.question.question_number,
            })

    # Recommendations
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

    # Section summary
    if is_hunter:
        _sections_ordered = [
            ("reading_comprehension", "Reading Comprehension"),
            ("quantitative_reasoning", "Quantitative Reasoning"),
            ("math_achievement", "Math Achievement"),
        ]
    elif attempt.test.is_drill:
        _sections_ordered = [("Math", "Math")]
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

    # Passage summary (Hunter only)
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

    # Import _parse_quant_comparison from views
    from .views import _parse_quant_comparison

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

    easy_wrong = [q for q in question_review if q["difficulty"] == "Easy" and not q["is_correct"] and not q["unanswered"]]
    unanswered_count = sum(1 for q in question_review if q["unanswered"])
    total_time_minutes = sum(s["time_minutes"] for s in section_summary_data)
    pacing_ok = total_time_minutes <= 170 if has_section_time else None

    return {
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


def _compute_hunter_dashboard_context(parent):
    """Compute Hunter dashboard data for a given parent. Used by tutor student detail."""
    import json as _json
    from collections import defaultdict

    attempts_asc = (
        TestAttempt.objects.filter(
            parent=parent, is_completed=True,
            test__is_drill=False, test__exam_type="hunter",
        )
        .select_related("test")
        .order_by("submitted_at")
    )
    attempts_desc = list(reversed(list(attempts_asc)))

    # Question counts per test per section
    from .models import Question as _Question
    _test_ids = {a.test_id for a in attempts_desc}
    q_counts = {}
    for _row in (
        _Question.objects.filter(test_id__in=_test_ids)
        .values("test_id", "section")
        .annotate(n=Count("id"))
    ):
        q_counts.setdefault(_row["test_id"], {})[_row["section"]] = _row["n"]

    # Score history
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
        e = baseline_entries[-1]
        e["seq"] = "Baseline"
        score_history.append(e)
    for i, e in enumerate(benchmark_entries, 1):
        e["seq"] = f"Benchmark {i}"
        score_history.append(e)

    # Per-attempt percentage scores
    from .hunter_views import _hunter_band
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

    # Skill accuracy
    from .hunter_views import _SKILL_LABEL_MAP
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

    focus_areas = [s for s in skill_accuracy_data if s["total"] >= 3][:3]

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

    return {
        "parent": parent,
        "attempts": attempts_desc[:5],
        "attempts_with_pct": attempts_with_pct,
        "score_history": score_history,
        "score_history_json": _json.dumps(score_history),
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


@_tutor_required
def tutor_student_detail(request, parent_id, exam_type="shsat"):
    tutor = request.user.tutor_profile
    ts = get_object_or_404(TutorStudent, tutor=tutor, parent_id=parent_id)
    is_hunter = exam_type == "hunter"
    if is_hunter:
        context = _compute_hunter_dashboard_context(ts.parent)
    else:
        context = _compute_dashboard_context(ts.parent)
    context["student_name"] = _get_student_display_name(ts)
    context["is_tutor_view"] = True
    context["exam_type"] = exam_type
    context["is_hunter"] = is_hunter
    context["active_tab"] = exam_type
    template = "shsat/tutor_student_detail_hunter.html" if is_hunter else "shsat/tutor_student_detail.html"
    return render(request, template, context)


@_tutor_required
def tutor_error_analysis(request, parent_id, attempt_id):
    tutor = request.user.tutor_profile
    ts = get_object_or_404(TutorStudent, tutor=tutor, parent_id=parent_id)
    attempt = get_object_or_404(TestAttempt, id=attempt_id, parent=ts.parent, is_completed=True)
    context = _compute_error_analysis_context(attempt)
    context["student_name"] = _get_student_display_name(ts)
    context["is_tutor_view"] = True
    context["parent_id"] = parent_id
    context["parent_template"] = "shsat/base_tutor.html"
    return render(request, "shsat/tutor_error_analysis.html", context)


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

@_tutor_required
def tutor_account(request):
    tutor = request.user.tutor_profile
    form = TutorAccountForm(request.POST or None, instance=tutor, user=request.user)
    if request.method == "POST" and "save_account" in request.POST and form.is_valid():
        form.save()
        messages.success(request, "Account updated.")
        return redirect("tutor_account")

    # Handle student nickname update
    if request.method == "POST" and "update_nickname" in request.POST:
        ts_id = request.POST.get("ts_id")
        nickname = request.POST.get("nickname", "").strip()
        ts = TutorStudent.objects.filter(id=ts_id, tutor=tutor).first()
        if ts:
            ts.nickname = nickname
            ts.save(update_fields=["nickname"])
            messages.success(request, "Student nickname updated.")
        return redirect("tutor_account")

    # Handle remove student
    if request.method == "POST" and "remove_student" in request.POST:
        ts_id = request.POST.get("ts_id")
        TutorStudent.objects.filter(id=ts_id, tutor=tutor).delete()
        messages.success(request, "Student removed.")
        return redirect("tutor_account")

    student_links = (
        TutorStudent.objects
        .filter(tutor=tutor)
        .select_related("parent__user")
        .order_by("added_at")
    )

    return render(request, "shsat/tutor_account.html", {
        "form": form,
        "tutor": tutor,
        "student_links": student_links,
    })


# ---------------------------------------------------------------------------
# Stripe subscription
# ---------------------------------------------------------------------------

TUTOR_TIERS = [
    {"name": "Starter", "students": 5, "price": "Free", "setting": ""},
    {"name": "Professional", "students": 25, "price": "$29/mo", "setting": "STRIPE_TUTOR_PRICE_ID_25"},
    {"name": "Unlimited", "students": 999, "price": "$79/mo", "setting": "STRIPE_TUTOR_PRICE_ID_UNL"},
]


@_tutor_required
def tutor_pricing(request):
    tutor = request.user.tutor_profile
    tiers = []
    for t in TUTOR_TIERS:
        tiers.append({
            "name": t["name"],
            "students": t["students"],
            "price": t["price"],
            "price_id": getattr(settings, t["setting"], "") if t["setting"] else "",
            "is_current": t["students"] == tutor.student_limit,
        })
    return render(request, "shsat/tutor_pricing.html", {
        "tutor": tutor,
        "tiers": tiers,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    })


@_tutor_required
@require_POST
def tutor_checkout(request):
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    tutor = request.user.tutor_profile
    price_id = request.POST.get("price_id", "")
    student_limit = request.POST.get("student_limit", "10")

    if not price_id:
        return redirect("tutor_pricing")

    success_url = request.build_absolute_uri("/tutor/checkout/success/") + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.build_absolute_uri("/tutor/pricing/")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(request.user.id),
        customer_email=request.user.email,
        metadata={
            "tutor_id": str(tutor.id),
            "student_limit": student_limit,
            "product_type": "tutor",
        },
    )
    return redirect(session.url, permanent=False)


@_tutor_required
def tutor_checkout_success(request):
    import stripe
    session_id = request.GET.get("session_id")
    if session_id:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                tutor = request.user.tutor_profile
                metadata = getattr(session, "metadata", {})
                student_limit = int(metadata.get("student_limit", "10")) if metadata else 10
                tutor.subscription_status = "active"
                tutor.student_limit = student_limit
                if hasattr(session, "subscription"):
                    tutor.stripe_subscription_id = session.subscription or ""
                if hasattr(session, "customer"):
                    tutor.stripe_customer_id = session.customer or ""
                tutor.save(update_fields=[
                    "subscription_status", "student_limit",
                    "stripe_subscription_id", "stripe_customer_id",
                ])
        except Exception:
            pass
    return render(request, "shsat/tutor_checkout_success.html")
