"""
Load items.json into the Item table.

Idempotent: upserts by (item_id, form_version).
Refuses to overwrite an item that already has responses unless --force.

Usage:
    python manage.py load_items axis5/docs/items.json
    python manage.py load_items axis5/docs/items.json --force
"""
import json
from django.core.management.base import BaseCommand, CommandError
from axis5.models import Item


class Command(BaseCommand):
    help = "Load items.json into the Item table (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to items.json")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite items that already have responses",
        )

    def handle(self, *args, **options):
        path = options["path"]
        force = options["force"]

        try:
            with open(path) as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        form_version = data["form"]["form_version"]
        rows = []

        # --- Calibration block: one Item, format tf_confidence_block, position 0 ---
        cal = data["calibration"]
        rows.append(
            {
                "item_id": cal["id"],
                "dimension": cal["dimension"],
                "format": "tf_confidence_block",
                "tier": None,
                "domain": "",
                "tag": "",
                "scored": True,
                "payload": cal,
                "position": 0,
            }
        )

        # --- Regular items: position 1..N ---
        for i, item in enumerate(data["items"], start=1):
            rows.append(
                {
                    "item_id": item["id"],
                    "dimension": item["dimension"],
                    "format": item["format"],
                    "tier": item.get("tier"),
                    "domain": item.get("domain", ""),
                    "tag": item.get("tag", ""),
                    "scored": item.get("scored", True),
                    "payload": item,
                    "position": i,
                }
            )

        created = updated = skipped = 0

        for row in rows:
            item_id = row["item_id"]
            try:
                existing = Item.objects.get(item_id=item_id, form_version=form_version)
                if existing.responses.exists() and not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  SKIP  {item_id}: has responses — use --force to overwrite"
                        )
                    )
                    skipped += 1
                    continue
                for k, v in row.items():
                    setattr(existing, k, v)
                existing.form_version = form_version
                existing.save()
                self.stdout.write(f"  UPDATE {item_id}")
                updated += 1
            except Item.DoesNotExist:
                Item.objects.create(**row, form_version=form_version)
                self.stdout.write(f"  CREATE {item_id}")
                created += 1

        total = Item.objects.filter(form_version=form_version, active=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone: {created} created, {updated} updated, {skipped} skipped."
                f"\nActive items for form_version={form_version}: {total}"
            )
        )
