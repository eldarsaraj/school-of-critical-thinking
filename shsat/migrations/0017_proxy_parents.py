from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("shsat", "0016_answer_essay_text"),
    ]

    operations = [
        migrations.CreateModel(
            name="SHSATParent",
            fields=[],
            options={
                "verbose_name": "SHSAT Parent",
                "verbose_name_plural": "SHSAT Parents",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("shsat.parent",),
        ),
        migrations.CreateModel(
            name="HunterParent",
            fields=[],
            options={
                "verbose_name": "Hunter Parent",
                "verbose_name_plural": "Hunter Parents",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("shsat.parent",),
        ),
    ]
