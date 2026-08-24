import hashlib
import json
import logging
import random
from statistics import median as stat_median

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LoginForm, SignupForm, StartForm
from .models import Item, Response, Result, Session
from .services.scoring import SCORING_VERSION, build_form_from_db, score_session

logger = logging.getLogger(__name__)

# Fields that must never reach the browser — answer keys and pole logic.
_STRIP = frozenset([
    "correct", "target", "answer", "pole", "key", "derivation", "trivial",
    "scoring", "combination_poles", "pole_rules", "special_rules",
    "wrong_poles", "gating",
    "review_rubric", "strong_answer_markers", "weak_answer_markers",
])


def _strip_payload(obj):
    """Recursively remove answer-key fields before sending to client."""
    if isinstance(obj, dict):
        return {k: _strip_payload(v) for k, v in obj.items() if k not in _STRIP}
    if isinstance(obj, list):
        return [_strip_payload(v) for v in obj]
    return obj


def _hash_ip(request):
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
    ip = ip.split(",")[0].strip()
    return hashlib.sha256(ip.encode()).hexdigest()


def _build_sequence(form_version=1):
    """
    Return ordered list of Item PKs for a new session.
    Scored items in fixed position order, with 2-3 field_test items
    inserted at random interior positions (never first or last).
    """
    scored = list(
        Item.objects.filter(form_version=form_version, active=True, field_test=False)
        .exclude(format="open_text")
        .order_by("position")
        .values_list("id", flat=True)
    )
    field_test = list(
        Item.objects.filter(form_version=form_version, active=True, field_test=True)
        .values_list("id", flat=True)
    )
    if not field_test:
        return scored

    n_insert = min(random.randint(2, 3), len(field_test))
    to_insert = random.sample(field_test, n_insert)
    seq = list(scored)
    for pk in to_insert:
        pos = random.randint(1, len(seq) - 1)  # never first (0) or last
        seq.insert(pos, pk)
    return seq


def _session_items(session):
    """Return ordered list of Item objects for this session."""
    if not session.item_sequence:
        return []
    by_pk = {item.id: item for item in Item.objects.filter(id__in=session.item_sequence)}
    return [by_pk[pk] for pk in session.item_sequence if pk in by_pk]


# ------------------------------------------------------------------ views


def start(request):
    if request.method == "POST":
        form = StartForm(request.POST)
        if form.is_valid():
            seq = _build_sequence()
            user = request.user if request.user.is_authenticated else None
            session = Session.objects.create(
                email=form.cleaned_data["email"],
                user=user,
                form_version=1,
                state="started",
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                ip_hash=_hash_ip(request),
                item_sequence=seq,
            )
            # Store token so signup can claim this session
            request.session["axis5_pending_token"] = str(session.token)
            return redirect("axis5:item", token=session.token, n=0)
    else:
        form = StartForm()
    return render(request, "axis5/start.html", {"form": form})


def item(request, token, n):
    session = get_object_or_404(Session, token=token)

    if session.state == "completed":
        return redirect("axis5:results", token=token)
    if session.state == "expired":
        return render(request, "axis5/expired.html")

    items = _session_items(session)
    if not items or n >= len(items):
        raise Http404

    current = items[n]

    if session.state == "started":
        session.state = "in_progress"
        session.save(update_fields=["state"])

    if request.method == "POST":
        return _post_item(request, session, current, items, n)

    # Two-step: check whether step 1 is already stored (resumable mid-item)
    step1_locked = False
    step1_value = None
    existing = Response.objects.filter(session=session, item=current).first()
    if existing and current.format == "two_step":
        v = existing.value or {}
        if "_step1_locked" in v:
            step1_locked = True
            step1_value = v.get("step1")

    completed_count = Response.objects.filter(session=session).exclude(
        item__format="two_step",
    ).count()
    # Count fully completed two_step items (both steps stored, no lock flag)
    completed_count += Response.objects.filter(
        session=session, item__format="two_step"
    ).exclude(value__has_key="_step1_locked").count()

    safe = _strip_payload(current.payload)
    progress_pct = round(completed_count * 100 / len(items)) if items else 0

    return render(request, "axis5/item.html", {
        "session": session,
        "item": current,
        "safe_payload": safe,
        "safe_payload_json": json.dumps(safe),
        "n": n,
        "prev_n": n - 1 if n > 0 else None,
        "total": len(items),
        "completed": completed_count,
        "progress_pct": progress_pct,
        "step1_locked": step1_locked,
        "step1_value": step1_value,
        "is_last": n == len(items) - 1,
    })


def _parse_response(request, current):
    """Parse POST body into a (value, error) pair for the given item."""
    fmt = current.format
    p = current.payload

    if fmt == "tf_confidence_block":
        result = []
        for cal in p["items"]:
            kid = cal["id"]
            ans_raw = request.POST.get(f"answer_{kid}")
            conf_raw = request.POST.get(f"confidence_{kid}")
            if ans_raw is None or conf_raw is None:
                return None, f"Please answer all 8 statements."
            try:
                conf = int(conf_raw)
            except (ValueError, TypeError):
                return None, "Invalid confidence value."
            if not (50 <= conf <= 100):
                return None, "Confidence must be between 50 and 100."
            result.append({"id": kid, "answer": ans_raw == "true", "confidence": conf})
        return result, None

    if fmt == "mc":
        chosen = request.POST.get("answer")
        if not chosen:
            return None, "Please select an answer."
        return chosen, None

    if fmt == "mc_multi":
        value = {}
        for part in p["parts"]:
            chosen = request.POST.get(f"part_{part['id']}")
            if not chosen:
                return None, "Please answer all parts."
            value[part["id"]] = chosen
        return value, None

    if fmt == "select_all":
        raw = request.POST.getlist("options")
        ids = [o["id"] for o in p["options"]]
        if ids and isinstance(ids[0], int):
            try:
                return [int(x) for x in raw], None
            except (ValueError, TypeError):
                return None, "Invalid selection."
        return raw, None

    if fmt == "scope_grid":
        value = {}
        for row in p["rows"]:
            chosen = request.POST.get(f"row_{row['id']}")
            if not chosen:
                return None, "Please answer every row."
            value[str(row["id"])] = chosen
        return value, None

    if fmt == "allocate":
        total_required = p.get("total", 100)
        value = {}
        for opt in p["options"]:
            raw = request.POST.get(f"alloc_{opt['id']}", "0")
            try:
                value[str(opt["id"])] = float(raw)
            except (ValueError, TypeError):
                return None, "Invalid allocation."
        s = sum(value.values())
        if abs(s - total_required) > 0.51:
            return None, f"Allocations must sum to {total_required} (yours: {s:.0f})."
        return value, None

    if fmt == "open_text":
        text = request.POST.get("text", "").strip()
        if not text:
            return None, "Please write a response."
        return text, None

    return None, f"Unknown format: {fmt}"


def _timing(request):
    try:
        ms_first = int(request.POST.get("ms_first") or 0) or None
        ms_total = int(request.POST.get("ms_total") or 0) or None
        n_changes = int(request.POST.get("n_changes") or 0)
    except (ValueError, TypeError):
        ms_first = ms_total = None
        n_changes = 0
    return ms_first, ms_total, n_changes


def _rerender(request, session, current, items, n, error, step1_locked=False, step1_value=None):
    safe = _strip_payload(current.payload)
    return render(request, "axis5/item.html", {
        "session": session,
        "item": current,
        "safe_payload": safe,
        "safe_payload_json": json.dumps(safe),
        "n": n,
        "total": len(items),
        "completed": 0,
        "error": error,
        "is_last": n == len(items) - 1,
        "step1_locked": step1_locked,
        "step1_value": step1_value,
    })


def _post_item(request, session, current, items, n):
    ms_first, ms_total, n_changes = _timing(request)

    if current.format == "two_step":
        # Step 1 must already be stored
        existing = Response.objects.filter(session=session, item=current).first()
        if existing is None or "_step1_locked" not in (existing.value or {}):
            return _rerender(request, session, current, items, n,
                             "Please submit Step 1 before continuing.")
        step1_val = existing.value["step1"]
        step2_raw = request.POST.get("step2")
        if not step2_raw:
            return _rerender(request, session, current, items, n,
                             "Please enter your Step 2 estimate.",
                             step1_locked=True, step1_value=step1_val)
        try:
            step2_val = float(step2_raw)
        except (ValueError, TypeError):
            return _rerender(request, session, current, items, n,
                             "Please enter a valid number.",
                             step1_locked=True, step1_value=step1_val)
        existing.value = {"step1": step1_val, "step2": step2_val}
        existing.ms_total = ms_total
        existing.n_changes = n_changes
        existing.save(update_fields=["value", "ms_total", "n_changes"])
    else:
        value, error = _parse_response(request, current)
        if error:
            return _rerender(request, session, current, items, n, error)
        Response.objects.update_or_create(
            session=session,
            item=current,
            defaults={"value": value, "ms_first": ms_first,
                      "ms_total": ms_total, "n_changes": n_changes},
        )

    next_n = n + 1
    if next_n < len(items):
        return redirect("axis5:item", token=session.token, n=next_n)
    return redirect("axis5:complete", token=session.token)


@require_POST
def step(request, token, n):
    """
    AJAX: save step 1 of a two_step item and return step 2 content.
    Server rejects if step 1 is already locked.
    """
    session = get_object_or_404(Session, token=token)
    if session.state == "completed":
        return JsonResponse({"error": "Session already completed."}, status=400)

    items = _session_items(session)
    if not items or n >= len(items):
        return JsonResponse({"error": "Item not found."}, status=404)

    current = items[n]
    if current.format != "two_step":
        return JsonResponse({"error": "Not a two_step item."}, status=400)

    existing = Response.objects.filter(session=session, item=current).first()
    if existing and "_step1_locked" in (existing.value or {}):
        return JsonResponse({"error": "Step 1 already submitted."}, status=400)

    step1_raw = request.POST.get("step1")
    if not step1_raw:
        return JsonResponse({"error": "step1 required."}, status=400)
    try:
        step1_val = float(step1_raw)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid value."}, status=400)

    ms_first = None
    try:
        ms_first = int(request.POST.get("ms_first") or 0) or None
    except (ValueError, TypeError):
        pass

    Response.objects.update_or_create(
        session=session,
        item=current,
        defaults={"value": {"step1": step1_val, "_step1_locked": True},
                  "ms_first": ms_first},
    )

    step2_safe = _strip_payload(current.payload.get("step2", {}))
    return JsonResponse({"ok": True, "step1": step1_val, "step2": step2_safe})


def complete(request, token):
    session = get_object_or_404(Session, token=token)
    if session.state == "completed":
        return redirect("axis5:results", token=token)

    form_data = build_form_from_db(session.form_version)

    raw = {}
    for resp in session.responses.select_related("item").all():
        if resp.item.format == "tf_confidence_block":
            raw["calibration"] = resp.value
        else:
            v = resp.value
            if isinstance(v, dict) and "_step1_locked" in v:
                continue  # incomplete two_step
            raw[resp.item.item_id] = v

    payload = score_session(form_data, raw)
    quality_flags = _quality_flags(session)

    Result.objects.update_or_create(
        session=session,
        defaults={
            "form_version": session.form_version,
            "scoring_version": SCORING_VERSION,
            "payload": payload,
            "quality_flags": quality_flags,
        },
    )
    session.state = "completed"
    session.completed_at = timezone.now()
    session.save(update_fields=["state", "completed_at"])

    if session.email:
        _send_email(session)

    return redirect("axis5:results", token=token)


def _quality_flags(session):
    flags = []
    responses = list(session.responses.select_related("item").all())

    if not responses:
        return ["incomplete"]

    # rapid_responding: >25% of items answered in under 5 seconds
    rapid = sum(1 for r in responses if r.ms_total is not None and r.ms_total < 5000)
    if responses and rapid / len(responses) > 0.25:
        flags.append("rapid_responding")

    # straightlining: all confidence sliders within 5 points of each other
    cal_resp = next((r for r in responses if r.item.format == "tf_confidence_block"), None)
    if cal_resp and isinstance(cal_resp.value, list):
        confs = [e.get("confidence") for e in cal_resp.value if "confidence" in e]
        if len(confs) >= 2 and (max(confs) - min(confs)) <= 5:
            flags.append("straightlining")

    # incomplete: any scored non-field-test item has no response
    scored_pks = set(
        Item.objects.filter(
            id__in=session.item_sequence, scored=True, field_test=False
        ).values_list("id", flat=True)
    )
    responded_pks = {r.item_id for r in responses}
    if scored_pks - responded_pks:
        flags.append("incomplete")

    return flags


def _send_email(session):
    from django.conf import settings
    from django.core.mail import send_mail

    url = f"https://schoolofcriticalthinking.org/axis5/results/{session.token}/"
    try:
        send_mail(
            subject="Your AXIS-5 results",
            message=(
                f"Your AXIS-5 Critical Thinking Assessment is complete.\n\n"
                f"View your results:\n{url}\n\n"
                f"Save this link — it is your permanent access to your results.\n\n"
                f"— The School of Critical Thinking"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[session.email],
            fail_silently=False,
        )
    except Exception:
        logger.warning("Failed to send AXIS-5 results email to %s", session.email)


def results(request, token):
    session = get_object_or_404(Session, token=token)
    try:
        result = session.result
    except Result.DoesNotExist:
        return render(request, "axis5/not_ready.html", {"session": session})

    payload = result.payload
    band_order = {"Misaligned": 0, "Emerging": 1, "Aligned": 2, "Robust": 3}
    dims_sorted = sorted(
        payload["dimensions"].items(),
        key=lambda x: band_order.get(x[1]["band"], 0),
    )

    # SVG chart coordinates for calibration panel (viewBox 0 0 200 200, inner 30-170)
    cal = payload.get("calibration")
    cal_chart = None
    if cal:
        cx = round(30 + cal["avg_confidence"] * 140, 1)
        cy = round(170 - cal["accuracy"] * 140, 1)
        cal_chart = {"cx": cx, "cy": cy}

    # Strongest pattern: lowest-band dimension with a direction
    strongest = None
    for _key, dim in dims_sorted:
        if dim.get("direction_label"):
            strongest = dim
            break

    from .services.scoring import FORM_META, DIMENSION_BLURBS
    return render(request, "axis5/results.html", {
        "session": session,
        "result": result,
        "payload": payload,
        "calibration": cal,
        "cal_chart": cal_chart,
        "dimensions": payload["dimensions"],
        "dims_sorted": dims_sorted,
        "strongest": strongest,
        "quality_flags": [f for f in result.quality_flags if f != "rapid_responding"],
        "poles_by_dim": FORM_META["poles"],
        "dim_blurbs": DIMENSION_BLURBS,
    })

# ------------------------------------------------------------------ auth


def ax_signup(request):
    if request.user.is_authenticated:
        return redirect("axis5:start")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            # Claim any pending anonymous session
            pending = request.session.pop("axis5_pending_token", None)
            if pending:
                try:
                    s = Session.objects.get(token=pending, user__isnull=True)
                    s.user = user
                    s.save(update_fields=["user"])
                except Session.DoesNotExist:
                    pass
            return redirect("axis5:start")
    else:
        form = SignupForm()
    return render(request, "axis5/signup.html", {"form": form})


def ax_login(request):
    if request.user.is_authenticated:
        return redirect("axis5:start")
    error = None
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect(request.GET.get("next") or "axis5:start")
            error = "Email or password incorrect."
    else:
        form = LoginForm()
    return render(request, "axis5/login.html", {"form": form, "error": error})


def ax_logout(request):
    logout(request)
    return redirect("axis5:start")


# ------------------------------------------------------------------ staff stats


@staff_member_required(login_url="/axis5/auth/login/")
def staff_item_stats(request):
    # Unflagged completed sessions only
    all_results = list(
        Result.objects
        .filter(quality_flags=[], session__state="completed")
        .select_related("session")
        .prefetch_related("session__responses__item")
    )
    n_total = Result.objects.filter(session__state="completed").count()
    n_flagged = n_total - len(all_results)

    if not all_results:
        return render(request, "axis5/staff_item_stats.html", {
            "n_sessions": 0, "n_flagged": n_flagged, "items_stats": [],
        })

    # Items to report on (scored, non-calibration, non-field-test)
    items_list = list(
        Item.objects.filter(active=True, scored=True, field_test=False)
        .exclude(format="tf_confidence_block")
        .order_by("position")
    )
    item_by_id = {it.item_id: it for it in items_list}

    # First pass: collect per-result data into memory
    result_data = []
    for result in all_results:
        payload = result.payload
        dim_scores = {d: payload["dimensions"][d]["correct"]
                      for d in payload["dimensions"]}
        payload_items = payload.get("items", {})
        resp_items = {}
        for r in result.session.responses.all():
            iid = r.item.item_id
            if r.item.format == "tf_confidence_block":
                continue
            pi = payload_items.get(iid)
            if pi is None or pi.get("scored") is False:
                continue
            resp_items[iid] = {
                "correct": pi.get("correct", False),
                "ms_total": r.ms_total,
                "value": r.value,
            }
        result_data.append((result, dim_scores, resp_items))

    # Compute top-third / bottom-third split per dimension
    dim_keys = list(all_results[0].payload["dimensions"].keys())
    dim_splits = {}
    for dim in dim_keys:
        scored = sorted(result_data, key=lambda x: x[1].get(dim, 0))
        third = max(1, len(scored) // 3)
        dim_splits[dim] = {
            "top": {rd[0].id for rd in scored[-third:]},
            "bottom": {rd[0].id for rd in scored[:third]},
        }

    # Second pass: accumulate item stats
    accum = {
        iid: {"correct": [], "secs": [], "options": {}, "top": [], "bottom": []}
        for iid in item_by_id
    }
    for result, _dim_scores, resp_items in result_data:
        for iid, rd in resp_items.items():
            if iid not in accum:
                continue
            item = item_by_id[iid]
            accum[iid]["correct"].append(rd["correct"])
            if rd["ms_total"]:
                accum[iid]["secs"].append(rd["ms_total"] / 1000)
            if item.format == "mc" and isinstance(rd["value"], str):
                accum[iid]["options"][rd["value"]] = (
                    accum[iid]["options"].get(rd["value"], 0) + 1
                )
            splits = dim_splits.get(item.dimension, {})
            if result.id in splits.get("top", set()):
                accum[iid]["top"].append(rd["correct"])
            if result.id in splits.get("bottom", set()):
                accum[iid]["bottom"].append(rd["correct"])

    # Build final stats list
    items_stats = []
    for iid, item in item_by_id.items():
        a = accum[iid]
        n = len(a["correct"])
        pct_frac = sum(a["correct"]) / n if n else None
        pct = round(pct_frac * 100) if pct_frac is not None else None
        med_secs = round(stat_median(a["secs"]), 1) if a["secs"] else None
        top_frac = sum(a["top"]) / len(a["top"]) if a["top"] else None
        bot_frac = sum(a["bottom"]) / len(a["bottom"]) if a["bottom"] else None
        items_stats.append({
            "item_id": iid,
            "dimension": item.dimension,
            "format": item.format,
            "n": n,
            "pct": pct,            # integer 0–100 for display
            "pct_frac": pct_frac,  # 0.0–1.0 for sort
            "med_secs": med_secs,
            "options": a["options"],
            "top_pct": round(top_frac * 100) if top_frac is not None else None,
            "bot_pct": round(bot_frac * 100) if bot_frac is not None else None,
        })

    # Sort by % correct ascending (broken / near-broken items first)
    items_stats.sort(key=lambda x: (x["pct_frac"] is None, x["pct_frac"] or 0))

    return render(request, "axis5/staff_item_stats.html", {
        "n_sessions": len(all_results),
        "n_flagged": n_flagged,
        "items_stats": items_stats,
    })
