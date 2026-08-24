"""
Rescore all completed sessions at a given scoring version.

Usage:
    python manage.py rescore_all --scoring-version=1

Result.payload is fully reproducible from Response rows. This command
re-derives it and overwrites Result.payload in place, useful after scoring
rule changes. The form payload is loaded from items.json on disk.
"""
import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from axis5.models import Session, Response, Result, Item
from axis5.services.scoring import score_session, SCORING_VERSION


def _build_form_from_db(form_version):
    """Reconstruct the items.json-shaped form dict from the Item table."""
    items_qs = Item.objects.filter(form_version=form_version, active=True).order_by("position")
    calibration_item = None
    regular_items = []
    for item in items_qs:
        if item.format == "tf_confidence_block":
            calibration_item = item.payload
        else:
            regular_items.append(item.payload)

    if calibration_item is None:
        raise CommandError(f"No calibration item found for form_version={form_version}")

    # Reconstruct the form metadata from the calibration item's sibling payload
    # (dimensions/poles are static; we inline them here to avoid a separate Form model lookup)
    form_meta = {
        "id": f"axis5-v{form_version}",
        "form_version": form_version,
        "scoring_version": SCORING_VERSION,
        "dimensions": {
            "U": "Uncertainty Handling",
            "M": "Model Awareness",
            "C": "Causal Reasoning",
            "A": "Abstraction Control",
            "E": "Trust Distribution",
        },
        "poles": {
            "U": {"minus": "paralysis", "plus": "overconfidence"},
            "M": {"minus": "literalism", "plus": "model nihilism"},
            "C": {"minus": "over-attribution", "plus": "causal agnosticism"},
            "A": {"minus": "overgeneralization", "plus": "particularism"},
            "E": {"minus": "rigidity", "plus": "over-deference"},
        },
    }
    return {"form": form_meta, "calibration": calibration_item, "items": regular_items}


class Command(BaseCommand):
    help = "Rescore all completed sessions and overwrite Result payloads."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scoring-version",
            type=int,
            default=SCORING_VERSION,
            help="Scoring version to apply (default: current)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without writing anything",
        )

    def handle(self, *args, **options):
        sv = options["scoring_version"]
        dry_run = options["dry_run"]

        sessions = Session.objects.filter(state="completed").select_related("result")
        self.stdout.write(f"Found {sessions.count()} completed sessions.")

        rescored = errors = unchanged = 0

        for session in sessions:
            try:
                form = _build_form_from_db(session.form_version)
            except CommandError as e:
                self.stdout.write(self.style.ERROR(f"  Session {session.pk}: {e}"))
                errors += 1
                continue

            # Build responses dict from stored Response rows
            raw_responses = {}
            for resp in session.responses.select_related("item").all():
                item_id = resp.item.item_id
                if resp.item.format == "tf_confidence_block":
                    raw_responses["calibration"] = resp.value
                else:
                    raw_responses[item_id] = resp.value

            new_payload = score_session(form, raw_responses)

            try:
                result = session.result
                if result.payload == new_payload and result.scoring_version == sv:
                    unchanged += 1
                    continue
                if dry_run:
                    self.stdout.write(f"  [dry-run] Would rescore session {session.pk}")
                else:
                    result.payload = new_payload
                    result.scoring_version = sv
                    result.computed_at = timezone.now()
                    result.save(update_fields=["payload", "scoring_version", "computed_at"])
                rescored += 1
            except Result.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  Session {session.pk}: no Result row, skipping")
                )
                errors += 1

        verb = "Would rescore" if dry_run else "Rescored"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb}: {rescored}, unchanged: {unchanged}, errors: {errors}"
            )
        )
