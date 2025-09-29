"""Create therapist treatment model."""

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("therapist_panel", "0003_remove_therapist_email"),
    ]

    operations = [
        migrations.CreateModel(
            name="TherapistTreatment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                (
                    "duration_minutes",
                    models.PositiveIntegerField(
                        help_text="Length of the session in minutes.",
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Charge for the session in local currency.",
                        max_digits=8,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treatments",
                        to="therapist_panel.therapist",
                    ),
                ),
            ],
            options={
                "ordering": ["therapist", "name"],
                "verbose_name": "Therapist treatment",
                "verbose_name_plural": "Therapist treatments",
            },
        ),
    ]
