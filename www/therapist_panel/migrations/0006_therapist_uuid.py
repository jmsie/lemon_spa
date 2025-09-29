"""Add UUID field to therapist."""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("therapist_panel", "0005_therapisttreatment_preparation_minutes"),
    ]

    operations = [
        migrations.AddField(
            model_name="therapist",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
