"""Add recurring time off series support."""

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("therapist_panel", "0007_therapist_timezone"),
        ("scheduling", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TherapistTimeOffSeries",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("repeat_type", models.CharField(choices=[("daily", "Daily"), ("weekly", "Weekly")], max_length=16)),
                ("repeat_interval", models.PositiveIntegerField(default=1)),
                ("start_date", models.DateField()),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("repeat_until", models.DateField(blank=True, null=True)),
                ("note", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="time_off_series",
                        to="therapist_panel.therapist",
                    ),
                ),
            ],
            options={
                "ordering": ["start_date", "start_time"],
                "verbose_name": "Therapist time off series",
                "verbose_name_plural": "Therapist time off series",
            },
        ),
        migrations.AddField(
            model_name="therapisttimeoff",
            name="is_skipped",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="therapisttimeoff",
            name="series",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="occurrences",
                to="scheduling.therapisttimeoffseries",
            ),
        ),
        migrations.AddIndex(
            model_name="therapisttimeoffseries",
            index=models.Index(
                fields=["therapist", "start_date"],
                name="time_off_series_start_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="therapisttimeoffseries",
            index=models.Index(
                fields=["therapist", "is_active"],
                name="time_off_series_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="therapisttimeoff",
            index=models.Index(fields=["series", "starts_at"], name="time_off_occurrence_idx"),
        ),
        migrations.AddIndex(
            model_name="therapisttimeoff",
            index=models.Index(fields=["therapist", "is_skipped"], name="time_off_skipped_idx"),
        ),
        migrations.AddConstraint(
            model_name="therapisttimeoff",
            constraint=models.UniqueConstraint(
                condition=models.Q(series__isnull=False),
                fields=("series", "starts_at"),
                name="therapist_time_off_unique_series_occurrence",
            ),
        ),
    ]
