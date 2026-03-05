import uuid
from django.db import migrations, models


def populate_tokens(apps, schema_editor):
    """Assign a unique UUID to every existing row."""
    DiagnosticLead = apps.get_model("diagnostic", "DiagnosticLead")
    for lead in DiagnosticLead.objects.all():
        lead.token = uuid.uuid4()
        lead.save(update_fields=["token"])


class Migration(migrations.Migration):

    dependencies = [
        ("diagnostic", "0003_alter_diagnosticlead_email"),
    ]

    operations = [
        # Step 1: add the column as nullable (no unique constraint yet)
        migrations.AddField(
            model_name="diagnosticlead",
            name="token",
            field=models.UUIDField(null=True, editable=False),
        ),
        # Step 2: fill every existing row with a unique UUID
        migrations.RunPython(populate_tokens, migrations.RunPython.noop),
        # Step 3: make it non-nullable and unique
        migrations.AlterField(
            model_name="diagnosticlead",
            name="token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
