"""
Management command to reorder Baseline Test ELA questions so R&E comes before RC,
and rename Practice Tests 1-4 to Benchmark Tests 1-4.
"""
from django.core.management.base import BaseCommand
from shsat.models import Question, Test

RE_SKILLS = {"punctuation", "usage_agreement", "sentence_structure"}

BASELINE_TEST_ID = 34
PRACTICE_TEST_IDS = {
    67:  "Benchmark Test 1",
    100: "Benchmark Test 2",
    133: "Benchmark Test 3",
    166: "Benchmark Test 4",
}


class Command(BaseCommand):
    help = "Reorder Baseline Test ELA (R&E first) and rename Practice Tests to Benchmark Tests"

    def handle(self, *args, **options):
        self._reorder_ela()
        self._rename_tests()

    def _reorder_ela(self):
        self.stdout.write("Reordering Baseline Test ELA questions...")
        stages = ["routing", "easy_module", "hard_module"]
        for stage in stages:
            qs = list(
                Question.objects.filter(
                    test_id=BASELINE_TEST_ID,
                    section="ELA",
                    stage=stage,
                ).order_by("question_number")
            )
            if not qs:
                self.stdout.write(f"  {stage}: no questions found, skipping")
                continue

            re_qs = [q for q in qs if q.skill in RE_SKILLS]
            rc_qs = [q for q in qs if q.skill not in RE_SKILLS]
            self.stdout.write(
                f"  {stage}: {len(qs)} total — {len(re_qs)} R&E, {len(rc_qs)} RC"
            )

            # Step 1: assign temp numbers (offset by 1000) to avoid unique_together conflicts
            for q in qs:
                q.question_number += 1000
                q.save(update_fields=["question_number"])

            # Step 2: assign final numbers — R&E first, then RC
            ordered = re_qs + rc_qs
            for i, q in enumerate(ordered, start=1):
                q.question_number = i
                q.save(update_fields=["question_number"])

            self.stdout.write(f"  {stage}: reordered OK")

        self.stdout.write(self.style.SUCCESS("ELA reordering complete."))

    def _rename_tests(self):
        self.stdout.write("Renaming Practice Tests to Benchmark Tests...")
        for test_id, new_title in PRACTICE_TEST_IDS.items():
            try:
                test = Test.objects.get(id=test_id)
                old_title = test.title
                test.title = new_title
                test.save(update_fields=["title"])
                self.stdout.write(f"  {old_title!r} → {new_title!r}")
            except Test.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Test ID {test_id} not found, skipping"))
        self.stdout.write(self.style.SUCCESS("Rename complete."))
