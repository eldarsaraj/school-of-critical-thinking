from django.core.management.base import BaseCommand
from shsat.models import CutoffScore

CUTOFFS_2025 = [
    ("Stuyvesant High School", "Stuyvesant", 562, 762),
    ("Bronx High School of Science", "Bronx Sci", 522, 749),
    ("Staten Island Technical HS", "SITH", 527, 387),
    ("Brooklyn Technical HS", "Brooklyn Tech", 478, 1766),
    ("HS of Math, Science & Engineering at City College", "HSMSE", 493, 135),
    ("HS of American Studies at Lehman College", "HSAS", 514, 144),
    ("Queens HS for the Sciences at York College", "QHSS", 472, 111),
    ("The Brooklyn Latin School", "Brooklyn Latin", 437, 262),
]


class Command(BaseCommand):
    help = "Seed CutoffScore table with 2025 admissions data"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for name, short, cutoff, seats in CUTOFFS_2025:
            obj, was_created = CutoffScore.objects.update_or_create(
                school_short=short,
                admissions_year=2025,
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
            self.style.SUCCESS(f"Done — {created} created, {updated} updated.")
        )
