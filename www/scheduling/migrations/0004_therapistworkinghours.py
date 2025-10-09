"""Add therapist working hours models."""

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("therapist_panel", "0007_therapist_timezone"),
        ("scheduling", "0003_rename_time_off_therapist_start_idx_scheduling__therapi_a3ea73_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TherapistWorkingHoursSeries",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("weekday", models.PositiveSmallIntegerField(choices=[(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")])),
                ("repeat_interval", models.PositiveIntegerField(default=1)),
                ("start_date", models.DateField()),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("repeat_until", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="working_hours_series",
                        to="therapist_panel.therapist",
                    ),
                ),
            ],
            options={
                "ordering": ["weekday", "start_time"],
                "verbose_name": "Therapist working hours series",
                "verbose_name_plural": "Therapist working hours series",
                "indexes": [
                    models.Index(fields=["therapist", "weekday"], name="wh_series_weekday_idx"),
                    models.Index(fields=["therapist", "is_active"], name="wh_series_active_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="TherapistWorkingHours",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("note", models.TextField(blank=True)),
                ("is_generated", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "series",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="occurrences",
                        to="scheduling.therapistworkinghoursseries",
                    ),
                ),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="working_hours",
                        to="therapist_panel.therapist",
                    ),
                ),
            ],
            options={
                "ordering": ["starts_at"],
                "verbose_name": "Therapist working hours",
                "verbose_name_plural": "Therapist working hours",
                "indexes": [
                    models.Index(fields=["therapist", "starts_at"], name="wh_hours_starts_idx"),
                    models.Index(fields=["therapist", "ends_at"], name="wh_hours_ends_idx"),
                    models.Index(fields=["series", "starts_at"], name="wh_hours_series_idx"),
                    models.Index(fields=["therapist", "is_generated"], name="wh_hours_generated_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="therapistworkinghours",
            constraint=models.CheckConstraint(
                check=models.Q(ends_at__gt=models.F("starts_at")),
                name="therapist_working_hours_end_after_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="therapistworkinghours",
            constraint=models.UniqueConstraint(
                condition=models.Q(series__isnull=False),
                fields=("series", "starts_at"),
                name="therapist_working_hours_unique_series_occurrence",
            ),
        ),
    ]
