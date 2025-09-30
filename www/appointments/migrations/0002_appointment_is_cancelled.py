"""Add cancellation flag to appointments."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="is_cancelled",
            field=models.BooleanField(default=False),
        ),
    ]
