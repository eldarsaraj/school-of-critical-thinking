import uuid

from django.db import migrations, models


def populate_verification_tokens(apps, schema_editor):
    Parent = apps.get_model("shsat", "Parent")
    for parent in Parent.objects.filter(email_verification_token=None):
        parent.email_verification_token = uuid.uuid4()
        parent.save(update_fields=["email_verification_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("shsat", "0010_add_parent_has_paid"),
    ]

    operations = [
        migrations.AddField(
            model_name="parent",
            name="email_verified",
            field=models.BooleanField(default=True),
        ),
        # Step 1: add without unique so existing rows can get values
        migrations.AddField(
            model_name="parent",
            name="email_verification_token",
            field=models.UUIDField(null=True, blank=True),
        ),
        # Step 2: populate unique tokens for existing rows
        migrations.RunPython(populate_verification_tokens, migrations.RunPython.noop),
        # Step 3: add the unique constraint
        migrations.AlterField(
            model_name="parent",
            name="email_verification_token",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
