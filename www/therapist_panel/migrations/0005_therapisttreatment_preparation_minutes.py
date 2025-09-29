"""Add preparation time to therapist treatments."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("therapist_panel", "0004_therapisttreatment"),
    ]

    operations = [
        migrations.AddField(
            model_name="therapisttreatment",
            name="preparation_minutes",
            field=models.PositiveIntegerField(
                default=20,
                help_text="Setup time required before the session begins.",
            ),
        ),
    ]
