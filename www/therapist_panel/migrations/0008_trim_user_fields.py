"""Remove person-level fields from Therapist in favour of AccountUser."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("therapist_panel", "0007_therapist_timezone"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="therapist",
            options={"ordering": ["user__last_name", "user__first_name"]},
        ),
        migrations.RemoveField(
            model_name="therapist",
            name="first_name",
        ),
        migrations.RemoveField(
            model_name="therapist",
            name="last_name",
        ),
        migrations.RemoveField(
            model_name="therapist",
            name="phone_number",
        ),
    ]
