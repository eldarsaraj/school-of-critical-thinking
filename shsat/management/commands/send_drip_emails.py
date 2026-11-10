"""
Daily drip email sender.  Run via Heroku Scheduler once per day:

    python manage.py send_drip_emails

Handles three email types:
  1. drip_day3  — 3 days after baseline, explains the top trap (unpaid only)
  2. drip_day7  — 7 days after baseline, urgency nudge (unpaid only)
  3. abandoned_test — 24h after starting a test that was never finished
"""

import re
from datetime import timedelta

from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from shsat.models import Answer, Parent, SentEmail, TestAttempt


class Command(BaseCommand):
    help = "Send scheduled drip and abandonment emails"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print what would be sent without actually sending",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        now = timezone.now()
        sent_count = 0

        # ------------------------------------------------------------------
        # 1. Drip Day 3: top-trap explanation (only if baseline had a trap)
        # ------------------------------------------------------------------
        day3_window_start = now - timedelta(days=3, hours=6)
        day3_window_end = now - timedelta(days=2, hours=18)

        for parent in self._unpaid_parents():
            if SentEmail.objects.filter(parent=parent, email_type="drip_day3").exists():
                continue

            baseline = self._baseline_attempt(parent)
            if not baseline:
                continue
            if not (day3_window_start <= baseline.submitted_at <= day3_window_end):
                continue

            trap_label, trap_count = self._top_trap(baseline)
            if not trap_label:
                continue

            exam = baseline.test.exam_type
            upgrade_url = self._abs_url(
                "/hunter/upgrade/" if exam == "hunter" else "/shsat/upgrade/"
            )

            body = render_to_string("shsat/email_drip_day3.html", {
                "test_title": baseline.test.title,
                "top_trap_label": trap_label,
                "top_trap_count": trap_count,
                "upgrade_url": upgrade_url,
            })

            subject = f'What "{trap_label}" is costing your child'
            if dry:
                self.stdout.write(f"  [DRY] Day 3 → {parent.user.email}: {subject}")
            else:
                self._send(parent, subject, body)
                SentEmail.objects.create(
                    parent=parent, email_type="drip_day3", attempt=baseline,
                )
            sent_count += 1

        # ------------------------------------------------------------------
        # 2. Drip Day 7: urgency nudge
        # ------------------------------------------------------------------
        day7_window_start = now - timedelta(days=7, hours=6)
        day7_window_end = now - timedelta(days=6, hours=18)

        for parent in self._unpaid_parents():
            if SentEmail.objects.filter(parent=parent, email_type="drip_day7").exists():
                continue

            baseline = self._baseline_attempt(parent)
            if not baseline:
                continue
            if not (day7_window_start <= baseline.submitted_at <= day7_window_end):
                continue

            exam = baseline.test.exam_type
            child_name = parent.child_nickname or "your child"
            upgrade_url = self._abs_url(
                "/hunter/upgrade/" if exam == "hunter" else "/shsat/upgrade/"
            )

            body = render_to_string("shsat/email_drip_day7.html", {
                "test_title": baseline.test.title,
                "child_name": child_name,
                "upgrade_url": upgrade_url,
            })

            subject = f"Is {child_name} improving?"
            if dry:
                self.stdout.write(f"  [DRY] Day 7 → {parent.user.email}: {subject}")
            else:
                self._send(parent, subject, body)
                SentEmail.objects.create(
                    parent=parent, email_type="drip_day7", attempt=baseline,
                )
            sent_count += 1

        # ------------------------------------------------------------------
        # 3. Abandoned tests: started 24h+ ago, not completed
        # ------------------------------------------------------------------
        abandon_cutoff = now - timedelta(hours=24)

        abandoned = (
            TestAttempt.objects.filter(
                is_completed=False,
                started_at__lte=abandon_cutoff,
                test__is_drill=False,
            )
            .select_related("parent", "parent__user", "test")
        )

        for attempt in abandoned:
            parent = attempt.parent
            if SentEmail.objects.filter(
                parent=parent, email_type="abandoned_test", attempt=attempt,
            ).exists():
                continue

            exam = attempt.test.exam_type
            dashboard_url = self._abs_url(
                "/hunter/dashboard/" if exam == "hunter" else "/shsat/dashboard/"
            )

            body = render_to_string("shsat/email_abandoned_test.html", {
                "test_title": attempt.test.title,
                "dashboard_url": dashboard_url,
            })

            subject = "Everything OK?"
            if dry:
                self.stdout.write(
                    f"  [DRY] Abandoned → {parent.user.email}: "
                    f"{attempt.test.title} (started {attempt.started_at:%b %d})"
                )
            else:
                self._send(parent, subject, body)
                SentEmail.objects.create(
                    parent=parent, email_type="abandoned_test", attempt=attempt,
                )
            sent_count += 1

        label = "Would send" if dry else "Sent"
        self.stdout.write(self.style.SUCCESS(f"{label} {sent_count} email(s)."))

    # -- helpers -----------------------------------------------------------

    def _unpaid_parents(self):
        """Parents who haven't paid for either platform."""
        return Parent.objects.filter(
            has_paid=False, hunter_has_paid=False,
        ).select_related("user")

    def _baseline_attempt(self, parent):
        """Most recent completed baseline for this parent (either platform)."""
        return (
            TestAttempt.objects.filter(
                parent=parent,
                is_completed=True,
                test__title__icontains="baseline",
                test__is_drill=False,
            )
            .select_related("test")
            .order_by("-submitted_at")
            .first()
        )

    def _top_trap(self, attempt):
        """Return (label, count) for the most common distractor trap on this attempt."""
        from shsat.forms import DISTRACTOR_CHOICES

        dist_label = {}
        for entry in DISTRACTOR_CHOICES:
            if isinstance(entry[1], (list, tuple)) and entry[0] not in ("",):
                for key, label in entry[1]:
                    dist_label[key] = label
            elif entry[0]:
                dist_label[entry[0]] = entry[1]

        answers = Answer.objects.filter(
            attempt=attempt, is_correct=False,
        ).select_related("question")

        counts = {}
        for ans in answers:
            if not ans.selected_answer:
                continue
            dt = ans.question.distractor_types or {}
            trap = dt.get(ans.selected_answer, "")
            if trap:
                raw = dist_label.get(trap, trap.replace("_", " ").title())
                clean = re.sub(r"^\([EM]\)\s*", "", raw)
                counts[clean] = counts.get(clean, 0) + 1

        if not counts:
            return None, 0
        top = max(counts, key=counts.get)
        return top, counts[top]

    def _send(self, parent, subject, html_body):
        try:
            send_mail(
                subject=subject,
                message="",
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[parent.user.email],
                html_message=html_body,
                fail_silently=True,
            )
        except Exception:
            pass

    def _abs_url(self, path):
        """Build an absolute URL. In production this is the Heroku domain."""
        from django.conf import settings
        base = getattr(settings, "SITE_URL", "https://schoolofcriticalthinking.org")
        return base.rstrip("/") + path
