"""Create log for questionnaire invitation SMS."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("therapist_panel", "0007_therapist_timezone"),
        ("appointments", "0003_therapistsmsnotificationlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppointmentQuestionnaireLog",
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
                ("message", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("sent", "Sent"), ("failed", "Failed")], max_length=12
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                (
                    "appointment",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="questionnaire_logs",
                        to="appointments.appointment",
                    ),
                ),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="questionnaire_logs",
                        to="therapist_panel.therapist",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="appointmentquestionnairelog",
            index=models.Index(
                fields=["appointment", "status"],
                name="appointments_appt_questionnaire_status_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="appointmentquestionnairelog",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="sent"),
                fields=("appointment",),
                name="unique_questionnaire_sent_per_appointment",
            ),
        ),
    ]
