"""Add timezone field to therapist profile."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("therapist_panel", "0006_therapist_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="therapist",
            name="timezone",
            field=models.CharField(
                default="Asia/Taipei",
                help_text="IANA timezone identifier describing the therapist's local time.",
                max_length=64,
            ),
        ),
    ]
