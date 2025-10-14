"""Add therapist SMS notification log."""

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("appointments", "0002_appointment_is_cancelled"),
        ("therapist_panel", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TherapistSmsNotificationLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("phone_number", models.CharField(max_length=32)),
                ("message", models.CharField(max_length=160)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=12,
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                (
                    "appointment",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="therapist_sms_logs",
                        to="appointments.appointment",
                    ),
                ),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="sms_notification_logs",
                        to="therapist_panel.therapist",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
