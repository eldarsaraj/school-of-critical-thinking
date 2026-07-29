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

@_hunter_required
def hunter_dashboard(request):
    parent = _get_hunter_parent(request)

    # Check email verification
    if not parent.email_verified and not request.user.is_staff:
        return redirect("hunter_verify_pending")

    attempts = (
        TestAttempt.objects.filter(parent=parent, is_completed=True, test__exam_type="hunter")
        .select_related("test")
        .order_by("-submitted_at")
    )

    # Build per-attempt score rows
    attempt_rows = []
    for a in attempts:
        rc = a.ela_correct or 0   # RC mapped to ela_correct in submission
        qr_ma = a.math_correct or 0  # QR + MA mapped to math_correct
        composite = a.composite_score or 0
        attempt_rows.append({
            "attempt": a,
            "rc_correct": rc,
            "qr_ma_correct": qr_ma,
            "composite": composite,
        })

    in_progress = (
        TestAttempt.objects.filter(parent=parent, is_completed=False, test__exam_type="hunter")
        .select_related("test")
        .order_by("-started_at")
        .first()
    )

    context = {
        "parent": parent,
        "attempt_rows": attempt_rows,
        "in_progress": in_progress,
        "total_completed": len(attempt_rows),
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
