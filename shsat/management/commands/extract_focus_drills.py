"""
Extract questions from full-length SHSAT tests into Focus Practice drills.

Cuts each test from ~114 visible questions (57 per section) to ~100 (50 per
section) by moving ~10 questions per section into a new drill test.

Target per section per stage:
    routing:     25  (was 28-29)
    easy_module: 25  (was 27-28)
    hard_module: 25  (was 28)

Passage groups are atomic — if any question in a group is moved, the whole
group moves. The algorithm prefers extracting standalone questions from the
end of each stage first, then full passage groups from the end.

Usage:
    python manage.py extract_focus_drills --dry-run
    python manage.py extract_focus_drills
    python manage.py extract_focus_drills --test-id 8
"""

from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shsat.models import Test, Question


TARGET_PER_STAGE = 25
# Maximum overshoot when a passage group forces us past the target
MAX_TOLERANCE = 3


def _pick_questions_to_extract(questions, target_keep):
    """
    Given a queryset of questions in a single (section, stage) group,
    return a list of question IDs to extract so that `target_keep` remain.

    Rules:
        1. Prefer standalone questions (no passage_group_id) from the end.
        2. If more are needed, take whole passage groups from the end.
        3. Passage groups are atomic — never split.
    """
    total = questions.count()
    to_remove = total - target_keep
    if to_remove <= 0:
        return []

    # Build ordered lists of standalone and passage-group question IDs
    # sorted by question_number descending (extract from end first)
    standalone_ids = list(
        questions.filter(passage_group_id="")
        .order_by("-question_number")
        .values_list("id", flat=True)
    )

    # Passage groups: group by passage_group_id, ordered by max question_number desc
    groups = defaultdict(list)
    for q in questions.exclude(passage_group_id="").order_by("question_number"):
        groups[q.passage_group_id].append(q.id)
    # Sort groups by their highest question number (descending) — extract from end
    sorted_groups = sorted(groups.items(), key=lambda g: max(g[1]), reverse=True)

    extracted = []
    remaining_to_remove = to_remove

    # Phase 1: standalone questions from end
    for qid in standalone_ids:
        if remaining_to_remove <= 0:
            break
        extracted.append(qid)
        remaining_to_remove -= 1

    # Phase 2: full passage groups from end (if still need more)
    for _gid, gids in sorted_groups:
        if remaining_to_remove <= 0:
            break
        group_size = len(gids)
        # Only take a group if we still need to remove at least 1 question
        # and the overshoot is within tolerance
        overshoot = group_size - remaining_to_remove
        if overshoot <= MAX_TOLERANCE:
            extracted.extend(gids)
            remaining_to_remove -= group_size

    return extracted


def _renumber_questions(questions_qs):
    """Renumber questions sequentially within each (section, stage) group."""
    groups = defaultdict(list)
    for q in questions_qs.order_by("section", "stage", "question_number"):
        groups[(q.section, q.stage)].append(q)

    updates = []
    for (_section, _stage), qs in groups.items():
        for i, q in enumerate(qs, start=1):
            if q.question_number != i:
                q.question_number = i
                updates.append(q)

    if updates:
        # Temporarily clear unique_together by setting high numbers to avoid clashes
        for i, q in enumerate(updates):
            q.question_number = 10000 + i
        Question.objects.bulk_update(updates, ["question_number"])
        # Now set the real numbers
        for (_section, _stage), qs in groups.items():
            for i, q in enumerate(qs, start=1):
                q.question_number = i
        Question.objects.bulk_update(
            [q for qs in groups.values() for q in qs], ["question_number"]
        )

    return len(updates)


class Command(BaseCommand):
    help = "Extract questions from full tests into focus practice drills"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them",
        )
        parser.add_argument(
            "--test-id",
            type=int,
            default=None,
            help="Process a single test by ID (default: all non-drill SHSAT tests)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        test_id = options["test_id"]

        if test_id:
            tests = Test.objects.filter(id=test_id, is_drill=False)
            if not tests.exists():
                raise CommandError(f"No non-drill test found with ID {test_id}")
        else:
            # Find all non-drill SHSAT tests that have routing/easy/hard stages
            # (i.e. 170-question adaptive-style tests, whether or not is_adaptive is set)
            candidate_ids = (
                Question.objects.filter(
                    test__exam_type="shsat", test__is_drill=False, stage="routing"
                )
                .values_list("test_id", flat=True)
                .distinct()
            )
            tests = Test.objects.filter(id__in=candidate_ids).exclude(
                title__startswith="Demo"
            ).exclude(title__startswith="Practice")

        if not tests.exists():
            self.stdout.write(self.style.WARNING("No tests to process."))
            return

        for test in tests.order_by("id"):
            self._process_test(test, dry_run)

    def _process_test(self, test, dry_run):
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Test: {test.title} (ID={test.id})")
        self.stdout.write(f"{'='*60}")

        all_extract_ids = []

        for section in ["ELA", "Math"]:
            for stage in ["routing", "easy_module", "hard_module"]:
                qs = test.questions.filter(section=section, stage=stage)
                count = qs.count()
                if count == 0:
                    continue

                extract_ids = _pick_questions_to_extract(qs, TARGET_PER_STAGE)
                keep_count = count - len(extract_ids)

                status = "OK" if keep_count == TARGET_PER_STAGE else f"±{abs(keep_count - TARGET_PER_STAGE)}"
                self.stdout.write(
                    f"  {section:5s} {stage:12s}: {count} → {keep_count} "
                    f"(extract {len(extract_ids)}) [{status}]"
                )

                # Verify passage group atomicity
                extracted_set = set(extract_ids)
                remaining_qs = qs.exclude(id__in=extracted_set)
                for q in remaining_qs:
                    if q.passage_group_id:
                        group_total = qs.filter(passage_group_id=q.passage_group_id).count()
                        group_remaining = remaining_qs.filter(passage_group_id=q.passage_group_id).count()
                        if group_remaining != group_total and group_remaining != 0:
                            self.stderr.write(
                                self.style.ERROR(
                                    f"    SPLIT PASSAGE GROUP: {q.passage_group_id} "
                                    f"({group_remaining}/{group_total} remaining)"
                                )
                            )
                            raise CommandError("Passage group would be split. Aborting.")

                all_extract_ids.extend(extract_ids)

        if not all_extract_ids:
            self.stdout.write("  Nothing to extract.")
            return

        # Summary
        ela_extract = Question.objects.filter(id__in=all_extract_ids, section="ELA").count()
        math_extract = Question.objects.filter(id__in=all_extract_ids, section="Math").count()
        self.stdout.write(
            f"\n  Total extract: {len(all_extract_ids)} "
            f"({ela_extract} ELA + {math_extract} Math)"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("  [DRY RUN] No changes made."))
            return

        with transaction.atomic():
            # Create the drill test
            drill_title = f"{test.title} — Focus Practice"
            drill, created = Test.objects.get_or_create(
                title=drill_title,
                exam_type=test.exam_type,
                defaults={
                    "is_drill": True,
                    "is_free": False,
                    "is_published": False,
                    "is_adaptive": False,
                    "source": test.source,
                    "order": test.order + 100,
                },
            )
            if not created:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Drill '{drill_title}' already exists (ID={drill.id}). "
                        f"Moving questions into it."
                    )
                )

            # Move questions to drill
            moved = Question.objects.filter(id__in=all_extract_ids).update(test=drill)
            self.stdout.write(f"  Moved {moved} questions → '{drill_title}' (ID={drill.id})")

            # Renumber remaining questions in original test
            remaining_renumbered = _renumber_questions(test.questions.all())
            self.stdout.write(f"  Renumbered {remaining_renumbered} questions in original test")

            # Renumber extracted questions in drill
            drill_renumbered = _renumber_questions(drill.questions.all())
            self.stdout.write(f"  Renumbered {drill_renumbered} questions in drill")

            # Final validation
            for section in ["ELA", "Math"]:
                for stage in ["routing", "easy_module", "hard_module"]:
                    remaining = test.questions.filter(section=section, stage=stage)
                    count = remaining.count()
                    if count == 0:
                        continue
                    nums = list(remaining.order_by("question_number").values_list("question_number", flat=True))
                    expected = list(range(1, count + 1))
                    if nums != expected:
                        self.stderr.write(
                            self.style.ERROR(
                                f"  NUMBERING ERROR in {section} {stage}: {nums[:5]}..."
                            )
                        )

            self.stdout.write(self.style.SUCCESS(f"  Done: {test.title}"))

            # Print final counts
            self.stdout.write(f"\n  Final counts for '{test.title}':")
            for section in ["ELA", "Math"]:
                parts = []
                for stage in ["routing", "easy_module", "hard_module"]:
                    c = test.questions.filter(section=section, stage=stage).count()
                    parts.append(f"{stage}={c}")
                self.stdout.write(f"    {section}: {', '.join(parts)}")

            self.stdout.write(f"\n  Drill counts for '{drill_title}':")
            for section in ["ELA", "Math"]:
                parts = []
                for stage in ["routing", "easy_module", "hard_module"]:
                    c = drill.questions.filter(section=section, stage=stage).count()
                    if c > 0:
                        parts.append(f"{stage}={c}")
                if parts:
                    self.stdout.write(f"    {section}: {', '.join(parts)}")
