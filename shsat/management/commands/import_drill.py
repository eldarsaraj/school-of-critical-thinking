"""
import_drill — load a focused-practice drill YAML into the database.

Usage:
    python manage.py import_drill shsat/tests/drills/Math_addition_questions_1.yaml \
        --title "Math Focus Set 1 — Problem Setup" \
        --description "30 math questions targeting the wrong-setup error pattern."

Re-running the command against the same title will update questions in place
(safe to re-import after editing the YAML).
"""

import yaml
from django.core.management.base import BaseCommand, CommandError

from shsat.models import Question, Test


SECTION_MAP = {"math": "Math", "ela": "ELA"}


class Command(BaseCommand):
    help = "Import a focused-practice drill from a flat YAML file."

    def add_arguments(self, parser):
        parser.add_argument("yaml_file", type=str, help="Path to the drill YAML file.")
        parser.add_argument("--title", required=True, type=str, help="Test title (used as unique key).")
        parser.add_argument("--description", default="", type=str)
        parser.add_argument("--order", default=200, type=int, help="Sort order (higher = further down the list).")

    def handle(self, *args, **options):
        yaml_path = options["yaml_file"]
        try:
            with open(yaml_path, encoding="utf-8") as f:
                rows = yaml.safe_load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {yaml_path}")

        if not isinstance(rows, list):
            raise CommandError("YAML must be a flat list of question dicts.")

        test, created = Test.objects.update_or_create(
            title=options["title"],
            defaults={
                "description": options["description"],
                "is_free": False,
                "is_published": True,
                "is_adaptive": False,
                "is_drill": True,
                "exam_type": "shsat",
                "order": options["order"],
            },
        )

        if not created:
            # Wipe existing questions so a re-import is clean.
            test.questions.all().delete()

        count = 0
        for row in rows:
            raw_section = str(row.get("section", "Math")).strip()
            section = SECTION_MAP.get(raw_section.lower(), raw_section)

            raw_stage = str(row.get("stage", "routing")).strip()

            def _str(val):
                return str(val).strip() if val is not None else ""

            Question.objects.create(
                test=test,
                section=section,
                stage=raw_stage,
                question_number=int(row["question_number"]),
                question_type="multiple_choice",
                topic=_str(row.get("topic")),
                skill=_str(row.get("skill")),
                difficulty=_str(row.get("difficulty", "medium")),
                distractor_types=row.get("distractor_types") or {},
                passage_group_id="",
                passage_title="",
                passage_text="",
                question_text=_str(row.get("question_text")),
                choice_a=_str(row.get("choice_a")),
                choice_b=_str(row.get("choice_b")),
                choice_c=_str(row.get("choice_c")),
                choice_d=_str(row.get("choice_d")),
                choice_e="",
                correct_answer=_str(row.get("correct_answer")).upper(),
                explanation=_str(row.get("explanation")),
            )
            count += 1

        verb = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} drill '{test.title}': {count} questions imported.")
        )
