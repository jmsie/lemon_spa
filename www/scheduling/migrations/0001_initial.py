"""Initial migration introducing therapist time off model."""

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("therapist_panel", "0007_therapist_timezone"),
    ]

    operations = [
        migrations.CreateModel(
            name="TherapistTimeOff",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="time_off_periods",
                        to="therapist_panel.therapist",
                    ),
                ),
            ],
            options={
                "ordering": ["starts_at"],
                "verbose_name": "Therapist time off",
                "verbose_name_plural": "Therapist time off",
            },
        ),
        migrations.AddIndex(
            model_name="therapisttimeoff",
            index=models.Index(fields=["therapist", "starts_at"], name="time_off_therapist_start_idx"),
        ),
        migrations.AddIndex(
            model_name="therapisttimeoff",
            index=models.Index(fields=["therapist", "ends_at"], name="time_off_therapist_end_idx"),
        ),
        migrations.AddConstraint(
            model_name="therapisttimeoff",
            constraint=models.CheckConstraint(
                check=models.Q(ends_at__gt=models.F("starts_at")),
                name="therapist_time_off_end_after_start",
            ),
        ),
    ]
