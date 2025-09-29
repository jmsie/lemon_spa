"""Add user linkage to therapist records."""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("therapist_panel", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="therapist",
            name="user",
            field=models.OneToOneField(
                on_delete=models.CASCADE,
                related_name="therapist_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
