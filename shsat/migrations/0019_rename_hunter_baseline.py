"""
Data migration: rename Hunter baseline test variants → "Baseline Test".
"""
from django.db import migrations


def rename_hunter_baseline(apps, schema_editor):
    Test = apps.get_model("shsat", "Test")
    for old_title in ("Hunter Baseline Test", "Test 1 (baseline)"):
        Test.objects.filter(exam_type="hunter", title=old_title).update(title="Baseline Test")


def reverse_rename(apps, schema_editor):
    Test = apps.get_model("shsat", "Test")
    Test.objects.filter(
        exam_type="hunter",
        title="Baseline Test",
    ).update(title="Hunter Baseline Test")


class Migration(migrations.Migration):

    dependencies = [
        ("shsat", "0018_publish_hunter_baseline"),
    ]

    operations = [
        migrations.RunPython(rename_hunter_baseline, reverse_rename),
    ]
