"""
Import an SHSAT practice test from a YAML file.

Usage:
    python manage.py import_test path/to/test.yaml

    # Replace questions (wipes existing questions for that test):
    python manage.py import_test path/to/test.yaml --replace
"""

import sys
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError

from shsat.models import Test, Question


def _load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _import_section(test, section_key, rows):
    """
    section_key: 'ELA' or 'Math'
    rows: list of question dicts from YAML
    Returns count of questions created.
    """
    # Track passage text per passage_id so we only store it on the first question
    passage_store = {}
    count = 0

    for row in rows:
        passage_id = row.get("passage_id", "")
        passage_title = ""
        passage_text = ""

        if passage_id:
            if passage_id not in passage_store:
                # First question in this passage group — store the text
                passage_store[passage_id] = {
                    "title": row.get("passage_title", ""),
                    "text": row.get("passage_text", ""),
                }
            passage_title = passage_store[passage_id]["title"]
            passage_text = passage_store[passage_id]["text"]

        choices = row.get("choices", {})

        Question.objects.create(
            test=test,
            section=section_key,
            question_number=row["number"],
            question_type=row.get("type", "multiple_choice"),
            topic=row.get("topic", ""),
            difficulty=row.get("difficulty", "medium"),
            passage_group_id=passage_id,
            passage_title=passage_title,
            passage_text=passage_text,
            question_text=row["question"].strip(),
            choice_a=str(choices.get("A", "")).strip(),
            choice_b=str(choices.get("B", "")).strip(),
            choice_c=str(choices.get("C", "")).strip(),
            choice_d=str(choices.get("D", "")).strip(),
            correct_answer=str(row["answer"]).strip().upper(),
            explanation=row.get("explanation", "").strip(),
        )
        count += 1

    return count


class Command(BaseCommand):
    help = "Import an SHSAT practice test from a YAML file"

    def add_arguments(self, parser):
        parser.add_argument("yaml_file", type=str, help="Path to the YAML question file")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing questions for this test before importing",
        )

    def handle(self, *args, **options):
        path = Path(options["yaml_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        data = _load_yaml(path)

        title = data.get("title")
        if not title:
            raise CommandError("YAML file must have a 'title' field.")

        test, created = Test.objects.get_or_create(
            title=title,
            defaults={
                "source": data.get("source", ""),
                "is_free": data.get("is_free", True),
                "is_published": data.get("is_published", True),
                "order": data.get("order", 0),
            },
        )

        if not created:
            if options["replace"]:
                deleted, _ = test.questions.all().delete()
                self.stdout.write(f"Replaced: deleted {deleted} existing questions.")
            else:
                existing = test.questions.count()
                if existing > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Test '{title}' already has {existing} questions. "
                            f"Use --replace to overwrite, or choose a different title."
                        )
                    )
                    sys.exit(1)

            # Update metadata fields in case they changed
            test.source = data.get("source", test.source)
            test.is_free = data.get("is_free", test.is_free)
            test.is_published = data.get("is_published", test.is_published)
            test.order = data.get("order", test.order)
            test.save()

        ela_rows = data.get("ela", [])
        math_rows = data.get("math", [])

        ela_count = _import_section(test, "ELA", ela_rows)
        math_count = _import_section(test, "Math", math_rows)

        self.stdout.write(self.style.SUCCESS(
            f"Imported '{title}': {ela_count} ELA + {math_count} Math = {ela_count + math_count} questions."
        ))
        self.stdout.write(f"  Test ID: {test.id}  |  Published: {test.is_published}  |  Free: {test.is_free}")
