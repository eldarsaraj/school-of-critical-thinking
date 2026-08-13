from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shsat", "0019_rename_hunter_baseline"),
    ]

    operations = [
        migrations.AddField(
            model_name="parent",
            name="hunter_has_paid",
            field=models.BooleanField(default=False),
        ),
    ]
