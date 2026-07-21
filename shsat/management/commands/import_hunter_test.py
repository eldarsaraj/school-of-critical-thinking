"""
Import a Hunter College High School test from a YAML file.

Usage:
    python manage.py import_hunter_test shsat/tests/hunter/T1_complete.yaml \
        --title "Hunter Baseline Test" [--replace]

YAML format expected:
    passages:       list of {id, title, text, ...}
    items:          list of reading_comprehension and quantitative/math questions
    writing_assignment: single essay prompt dict
"""

import yaml
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from shsat.models import Test, Question


class Command(BaseCommand):
    help = "Import a Hunter test from YAML"

    def add_arguments(self, parser):
        parser.add_argument("yaml_file", type=str)
        parser.add_argument("--title", type=str, default="")
        parser.add_argument("--replace", action="store_true", help="Delete existing questions before import")

    def handle(self, *args, **options):
        path = Path(options["yaml_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        title = options["title"] or data.get("test_id") or path.stem

        test, created = Test.objects.get_or_create(
            title=title,
            defaults={
                "exam_type": "hunter",
                "is_free": False,
                "is_published": False,
                "is_adaptive": False,
            },
        )
        if not created:
            test.exam_type = "hunter"
            test.is_adaptive = False
            test.save(update_fields=["exam_type", "is_adaptive"])

        if options["replace"]:
            deleted, _ = test.questions.all().delete()
            self.stdout.write(f"Deleted {deleted} existing questions.")

        # Build passage lookup
        passages = {p["id"]: p for p in (data.get("passages") or [])}

        # Import items
        items = data.get("items") or []
        counts = {}
        for item in items:
            section = item.get("section", "")
            passage_id = item.get("passage_id") or ""
            passage = passages.get(passage_id) if passage_id else None

            # Normalise choice_e: Hunter QR/MA have choice_e: null
            choice_e = item.get("choice_e") or ""

            distractor_types = item.get("distractor_types") or {}
            if not isinstance(distractor_types, dict):
                distractor_types = {}

            Question.objects.update_or_create(
                test=test,
                section=section,
                stage="standard",
                question_number=item.get("question_number", 0),
                defaults=dict(
                    question_type="multiple_choice",
                    skill=str(item.get("skill") or "")[:50],
                    difficulty=item.get("difficulty", "medium"),
                    distractor_types=distractor_types,
                    passage_group_id=passage_id,
                    passage_title=passage["title"] if passage else "",
                    passage_text=passage["text"] if passage else "",
                    question_text=item.get("question_text", ""),
                    choice_a=item.get("choice_a") or "",
                    choice_b=item.get("choice_b") or "",
                    choice_c=item.get("choice_c") or "",
                    choice_d=item.get("choice_d") or "",
                    choice_e=choice_e,
                    correct_answer=item.get("correct_answer", ""),
                    explanation=item.get("explanation") or "",
                ),
            )
            counts[section] = counts.get(section, 0) + 1

        # Import writing assignment
        writing = data.get("writing_assignment")
        if writing:
            Question.objects.update_or_create(
                test=test,
                section="writing",
                stage="standard",
                question_number=1,
                defaults=dict(
                    question_type="essay",
                    skill="",
                    difficulty=writing.get("difficulty", "hard"),
                    distractor_types={},
                    passage_group_id="",
                    passage_title="",
                    passage_text="",
                    question_text=writing.get("prompt", ""),
                    choice_a="",
                    choice_b="",
                    choice_c="",
                    choice_d="",
                    choice_e="",
                    correct_answer="",
                    explanation="",
                ),
            )
            counts["writing"] = 1

        total = sum(counts.values())
        self.stdout.write(self.style.SUCCESS(
            f"Imported '{title}': " +
            ", ".join(f"{v} {k}" for k, v in counts.items()) +
            f" = {total} questions total."
        ))
