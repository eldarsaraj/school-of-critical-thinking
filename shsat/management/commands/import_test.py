"""
Import an SHSAT practice test from a YAML file.

Usage:
    python manage.py import_test path/to/test.yaml

    # Replace questions (wipes existing questions for that test):
    python manage.py import_test path/to/test.yaml --replace

YAML format for adaptive tests:
    Each question in the ela/math lists should include:
      stage: routing | easy_module | hard_module   (default: standard)
      skill: grammar_mechanics | rhetoric_organization | literal_comprehension |
             inference_analysis | vocabulary | number_operations | algebraic_reasoning |
             geometric_reasoning | data_probability | multistep_reasoning
      distractors:          # optional — maps wrong-answer letters to trap type
        B: partial_answer
        C: misread_question
        D: off_by_operation
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

    # E/F/G/H → A/B/C/D normalisation (for R&E Part B answer choices)
    _efgh_to_abcd = {"E": "A", "F": "B", "G": "C", "H": "D"}

    def _norm_answer(ans):
        a = str(ans).strip().upper()
        return _efgh_to_abcd.get(a, a)

    def _norm_distractors(raw):
        if not raw:
            return {}
        result = {}
        for letter, trap in raw.items():
            normalized_letter = _efgh_to_abcd.get(str(letter).upper(), str(letter).upper())
            result[normalized_letter] = str(trap).strip()
        return result

    for row in rows:
        # Support both naming conventions: passage_group_id (new) and passage_id (old)
        passage_id = row.get("passage_group_id") or row.get("passage_id", "")
        passage_title = ""
        passage_text = ""

        if passage_id:
            if passage_id not in passage_store:
                passage_store[passage_id] = {
                    "title": row.get("passage_title", ""),
                    "text": row.get("passage_text", ""),
                }
            passage_title = passage_store[passage_id]["title"]
            passage_text = passage_store[passage_id]["text"]

        # Support both naming conventions for choices
        choices = row.get("choices", {})

        def _norm_choice(key):
            # Try flat keys first (choice_a, choice_b …), then nested choices dict
            flat = row.get(f"choice_{key.lower()}", "")
            if flat:
                return str(flat).strip()
            val = choices.get(key) or choices.get(_efgh_to_abcd.get(key, ""), "")
            return str(val).strip() if val else ""

        Question.objects.create(
            test=test,
            section=section_key,
            stage=row.get("stage", "standard"),
            # Support both question_number (new) and number (old)
            question_number=row.get("question_number") or row["number"],
            # Support both question_type (new) and type (old)
            question_type=row.get("question_type") or row.get("type", "multiple_choice"),
            topic=row.get("topic", ""),
            skill=row.get("skill", ""),
            difficulty=row.get("difficulty", "medium"),
            distractor_types=_norm_distractors(row.get("distractors", {})),
            passage_group_id=passage_id,
            passage_title=passage_title,
            passage_text=passage_text,
            # Support both question_text (new) and question (old)
            question_text=(row.get("question_text") or row.get("question", "")).strip(),
            choice_a=_norm_choice("A"),
            choice_b=_norm_choice("B"),
            choice_c=_norm_choice("C"),
            choice_d=_norm_choice("D"),
            # Support both correct_answer (new) and answer (old)
            correct_answer=_norm_answer(row.get("correct_answer") or row.get("answer", "")),
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
                "is_adaptive": data.get("is_adaptive", False),
                "routing_threshold": data.get("routing_threshold", 0.60),
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
            test.is_adaptive = data.get("is_adaptive", test.is_adaptive)
            test.routing_threshold = data.get("routing_threshold", test.routing_threshold)
            test.save()

        ela_rows = data.get("ela", [])
        math_rows = data.get("math", [])

        ela_count = _import_section(test, "ELA", ela_rows)
        math_count = _import_section(test, "Math", math_rows)

        self.stdout.write(self.style.SUCCESS(
            f"Imported '{title}': {ela_count} ELA + {math_count} Math = {ela_count + math_count} questions."
        ))
        adaptive_str = f"  Adaptive: YES (threshold {test.routing_threshold:.0%})" if test.is_adaptive else "  Adaptive: no"
        self.stdout.write(f"  Test ID: {test.id}  |  Published: {test.is_published}  |  Free: {test.is_free}")
        self.stdout.write(adaptive_str)
