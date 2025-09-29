"""Remove redundant email column from therapist."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("therapist_panel", "0002_therapist_user"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="therapist",
            name="email",
        ),
    ]
