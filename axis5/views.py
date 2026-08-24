import hashlib
import json
import logging
import random

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import StartForm
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
            session = Session.objects.create(
                email=form.cleaned_data["email"],
                form_version=1,
                state="started",
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                ip_hash=_hash_ip(request),
                item_sequence=seq,
            )
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

    return render(request, "axis5/item.html", {
        "session": session,
        "item": current,
        "safe_payload": safe,
        "safe_payload_json": json.dumps(safe),
        "n": n,
        "total": len(items),
        "completed": completed_count,
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

    return render(request, "axis5/results.html", {
        "session": session,
        "result": result,
        "payload": payload,
        "calibration": payload.get("calibration"),
        "dimensions": payload["dimensions"],
        "dims_sorted": dims_sorted,
        "quality_flags": result.quality_flags,
    })
