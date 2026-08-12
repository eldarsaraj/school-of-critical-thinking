"""
Data migration: publish the Hunter Baseline Test so non-staff users can access it.
"""
from django.db import migrations


def publish_hunter_baseline(apps, schema_editor):
    Test = apps.get_model("shsat", "Test")
    Test.objects.filter(
        exam_type="hunter",
        title__icontains="baseline",
    ).update(is_published=True)


def unpublish_hunter_baseline(apps, schema_editor):
    Test = apps.get_model("shsat", "Test")
    Test.objects.filter(
        exam_type="hunter",
        title__icontains="baseline",
    ).update(is_published=False)


class Migration(migrations.Migration):

    dependencies = [
        ("shsat", "0017_proxy_parents"),
    ]

    operations = [
        migrations.RunPython(publish_hunter_baseline, unpublish_hunter_baseline),
    ]
