from django.core.management.base import BaseCommand
from shsat.models import CutoffScore

CUTOFFS_2026 = [
    ("Stuyvesant High School", "Stuyvesant", 561, 762),
    ("Bronx High School of Science", "Bronx Sci", 525, 749),
    ("Staten Island Technical HS", "SITH", 517, 387),
    ("Brooklyn Technical HS", "Brooklyn Tech", 506, 1766),
    ("HS of Math, Science & Engineering at City College", "HSMSE", 539, 135),
    ("HS of American Studies at Lehman College", "HSAS", 507, 144),
    ("Queens HS for the Sciences at York College", "QHSS", 531, 111),
    ("The Brooklyn Latin School", "Brooklyn Latin", 495, 262),
]


class Command(BaseCommand):
    help = "Seed CutoffScore table with 2026 admissions data"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for name, short, cutoff, seats in CUTOFFS_2026:
            obj, was_created = CutoffScore.objects.update_or_create(
                school_short=short,
                admissions_year=2026,
                defaults={
                    "school_name": name,
                    "cutoff_score": cutoff,
                    "approximate_seats": seats,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"Done (2026 cutoffs) — {created} created, {updated} updated.")
        )
