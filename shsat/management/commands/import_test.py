"""
Import an SHSAT practice test from a YAML file.

Usage:
    # Dict format (has title: key + ela:/math: sections):
    python manage.py import_test path/to/test.yaml

    # Flat-array format (list of dicts, each with a section: field):
    python manage.py import_test path/to/test.yaml --title "Baseline Test" --free --published

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
    section_key: 'ELA', 'Math', or None (Hunter — use each row's own 'section' field).
    rows: list of question dicts from YAML
    Returns count of questions created.
    """
    # Track passage text per passage_id so we only store it on the first question
    passage_store = {}
    count = 0

    # E/F/G/H → A/B/C/D normalisation (for R&E Part B answer choices)
    _efgh_to_abcd = {"E": "A", "F": "B", "G": "C", "H": "D"}

    def _norm_answer(ans, has_five_choices=False):
        a = str(ans).strip().upper()
        if has_five_choices:
            return a
        return _efgh_to_abcd.get(a, a)

    def _norm_distractors(raw, has_five_choices=False):
        if not raw:
            return {}
        result = {}
        for letter, trap in raw.items():
            l = str(letter).upper()
            normalized_letter = l if has_five_choices else _efgh_to_abcd.get(l, l)
            result[normalized_letter] = str(trap).strip()
        return result

    for row in rows:
        has_five_choices = bool(str(row.get("choice_e", "")).strip())

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
            section=section_key if section_key is not None else str(row.get("section", "")),
            stage=row.get("stage", "standard"),
            # Support both question_number (new) and number (old)
            question_number=row.get("question_number") or row["number"],
            # Support both question_type (new) and type (old)
            question_type=row.get("question_type") or row.get("type", "multiple_choice"),
            topic=row.get("topic", ""),
            skill=row.get("skill", ""),
            difficulty=row.get("difficulty", "medium"),
            distractor_types=_norm_distractors(row.get("distractor_types") or row.get("distractors") or {}, has_five_choices),
            passage_group_id=passage_id,
            passage_title=passage_title,
            passage_text=passage_text,
            # Support both question_text (new) and question (old)
            question_text=(row.get("question_text") or row.get("question", "")).strip(),
            choice_a=_norm_choice("A"),
            choice_b=_norm_choice("B"),
            choice_c=_norm_choice("C"),
            choice_d=_norm_choice("D"),
            choice_e=_norm_choice("E"),
            # Support both correct_answer (new) and answer (old)
            correct_answer=_norm_answer(row.get("correct_answer") or row.get("answer", ""), has_five_choices),
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
        # Flat-array format options (required when YAML is a bare list)
        parser.add_argument("--title", type=str, default="", help="Test title (required for flat-array YAML)")
        parser.add_argument("--free", action="store_true", default=False, help="Mark test as free")
        parser.add_argument("--published", action="store_true", default=False, help="Mark test as published")
        parser.add_argument("--adaptive", action="store_true", default=False, help="Mark test as adaptive")
        parser.add_argument("--source", type=str, default="", help="Test source label")
        parser.add_argument("--order", type=int, default=0, help="Display order")

    def handle(self, *args, **options):
        path = Path(options["yaml_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        raw = _load_yaml(path)

        _HUNTER_SECTIONS = {"reading_comprehension", "writing", "quantitative_reasoning", "math_achievement"}

        # Auto-detect flat-array vs dict format
        if isinstance(raw, list):
            title = options["title"]
            if not title:
                raise CommandError(
                    "YAML is a flat list. Provide a title with --title 'My Test Title'."
                )
            # Detect Hunter vs SHSAT by section names
            sections_present = {str(r.get("section", "")).lower() for r in raw}
            is_hunter = bool(sections_present & _HUNTER_SECTIONS)

            if is_hunter:
                hunter_rows = raw  # preserve native section per question
                ela_rows = math_rows = []
            else:
                ela_rows = [r for r in raw if str(r.get("section", "")).upper() == "ELA"]
                math_rows = [r for r in raw if str(r.get("section", "")).upper() == "MATH"]
                hunter_rows = []

            meta = {
                "source": options["source"],
                "is_free": options["free"],
                "is_published": options["published"],
                "is_adaptive": options["adaptive"],
                "routing_threshold": 0.60,
                "order": options["order"],
                "exam_type": "hunter" if is_hunter else "shsat",
            }
        else:
            # Dict format: YAML has a 'title' key and ela:/math: sections
            data = raw
            title = data.get("title") or options["title"]
            if not title:
                raise CommandError("YAML file must have a 'title' field (or pass --title).")
            ela_rows = data.get("ela", [])
            math_rows = data.get("math", [])
            hunter_rows = []
            meta = {
                "source": data.get("source", options["source"]),
                "is_free": data.get("is_free", options["free"]),
                "is_published": data.get("is_published", options["published"]),
                "is_adaptive": data.get("is_adaptive", options["adaptive"]),
                "routing_threshold": data.get("routing_threshold", 0.60),
                "order": data.get("order", options["order"]),
                "exam_type": data.get("exam_type", "shsat"),
            }

        test, created = Test.objects.get_or_create(title=title, defaults=meta)

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
            for k, v in meta.items():
                setattr(test, k, v)
            test.save()

        if hunter_rows:
            # Import each Hunter question preserving its native section
            total = _import_section(test, None, hunter_rows)
            by_section = {}
            for r in hunter_rows:
                s = str(r.get("section", "unknown"))
                by_section[s] = by_section.get(s, 0) + 1
            summary = " + ".join(f"{v} {k}" for k, v in sorted(by_section.items()))
            self.stdout.write(self.style.SUCCESS(
                f"Imported '{title}' (Hunter): {summary} = {total} questions."
            ))
        else:
            ela_count = _import_section(test, "ELA", ela_rows)
            math_count = _import_section(test, "Math", math_rows)
            self.stdout.write(self.style.SUCCESS(
                f"Imported '{title}': {ela_count} ELA + {math_count} Math = {ela_count + math_count} questions."
            ))

        adaptive_str = f"  Adaptive: YES (threshold {test.routing_threshold:.0%})" if test.is_adaptive else "  Adaptive: no"
        self.stdout.write(f"  Test ID: {test.id}  |  Published: {test.is_published}  |  Free: {test.is_free}  |  Exam: {test.exam_type}")
        self.stdout.write(adaptive_str)
