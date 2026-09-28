"""
Consolidate per-test Focus Practice drills into section-based Focus Sets.

Takes the extracted questions from "… — Focus Practice" drills and
reorganises them into ELA and Math Focus Sets of ~25-30 questions each,
matching the format of the existing "Math Focus Set 1 — Problem Setup".

Usage:
    python manage.py consolidate_focus_drills --dry-run
    python manage.py consolidate_focus_drills
"""

import math

from django.core.management.base import BaseCommand
from django.db import transaction

from shsat.models import Test, Question


SET_SIZE = 25  # target questions per focus set


class Command(BaseCommand):
    help = "Consolidate Focus Practice drills into ELA and Math Focus Sets"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Gather all Focus Practice drills
        drills = Test.objects.filter(
            title__endswith="Focus Practice", is_drill=True
        ).order_by("id")

        if not drills.exists():
            self.stdout.write(self.style.WARNING("No Focus Practice drills found."))
            return

        # Collect all questions by section, ordered by source drill then question_number
        ela_questions = list(
            Question.objects.filter(test__in=drills, section="ELA")
            .order_by("test__id", "stage", "question_number")
            .values_list("id", flat=True)
        )
        math_questions = list(
            Question.objects.filter(test__in=drills, section="Math")
            .order_by("test__id", "stage", "question_number")
            .values_list("id", flat=True)
        )

        self.stdout.write(f"Found {len(ela_questions)} ELA + {len(math_questions)} Math questions")

        # Determine numbering: find existing focus sets to continue numbering
        existing_ela = Test.objects.filter(
            title__startswith="ELA Focus Set", is_drill=True
        ).count()
        existing_math = Test.objects.filter(
            title__startswith="Math Focus Set", is_drill=True
        ).count()

        ela_start = existing_ela + 1
        math_start = existing_math + 1

        # Split into chunks
        ela_chunks = _split_evenly(ela_questions, SET_SIZE)
        math_chunks = _split_evenly(math_questions, SET_SIZE)

        self.stdout.write(f"\nWill create {len(ela_chunks)} ELA Focus Set(s) (starting at #{ela_start})")
        for i, chunk in enumerate(ela_chunks):
            self.stdout.write(f"  ELA Focus Set {ela_start + i}: {len(chunk)} questions")

        self.stdout.write(f"\nWill create {len(math_chunks)} Math Focus Set(s) (starting at #{math_start})")
        for i, chunk in enumerate(math_chunks):
            self.stdout.write(f"  Math Focus Set {math_start + i}: {len(chunk)} questions")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No changes made."))
            return

        with transaction.atomic():
            # Create ELA Focus Sets
            for i, chunk in enumerate(ela_chunks):
                set_num = ela_start + i
                title = f"ELA Focus Set {set_num}"
                test = Test.objects.create(
                    title=title,
                    is_drill=True,
                    is_free=False,
                    is_published=True,
                    is_adaptive=False,
                    exam_type="shsat",
                    order=200 + set_num,
                )
                _move_and_renumber(chunk, test)
                self.stdout.write(self.style.SUCCESS(
                    f"  Created '{title}' (ID={test.id}): {len(chunk)} questions"
                ))

            # Create Math Focus Sets
            for i, chunk in enumerate(math_chunks):
                set_num = math_start + i
                title = f"Math Focus Set {set_num}"
                test = Test.objects.create(
                    title=title,
                    is_drill=True,
                    is_free=False,
                    is_published=True,
                    is_adaptive=False,
                    exam_type="shsat",
                    order=200 + set_num,
                )
                _move_and_renumber(chunk, test)
                self.stdout.write(self.style.SUCCESS(
                    f"  Created '{title}' (ID={test.id}): {len(chunk)} questions"
                ))

            # Delete the now-empty Focus Practice drills
            for drill in drills:
                remaining = drill.questions.count()
                if remaining == 0:
                    self.stdout.write(f"  Deleted empty drill: '{drill.title}' (ID={drill.id})")
                    drill.delete()
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  Kept drill '{drill.title}' — still has {remaining} questions"
                    ))

        self.stdout.write(self.style.SUCCESS("\nDone."))


def _split_evenly(items, target_size):
    """Split a list into chunks of roughly equal size, each close to target_size."""
    total = len(items)
    if total == 0:
        return []
    num_chunks = max(1, round(total / target_size))
    chunk_size = math.ceil(total / num_chunks)
    return [items[i:i + chunk_size] for i in range(0, total, chunk_size)]


def _move_and_renumber(question_ids, target_test):
    """Move questions to target test one at a time with unique numbering.

    Avoids unique_together clashes by assigning a unique question_number
    as each question is moved.
    """
    questions = list(Question.objects.filter(id__in=question_ids).order_by("section", "stage", "question_number"))
    for i, q in enumerate(questions, start=1):
        q.test = target_test
        q.question_number = i
        q.stage = "routing"  # drills don't use adaptive stages
        q.save(update_fields=["test", "question_number", "stage"])
