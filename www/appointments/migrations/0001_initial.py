"""Create appointment model."""

import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("therapist_panel", "0005_therapisttreatment_preparation_minutes"),
    ]

    operations = [
        migrations.CreateModel(
            name="Appointment",
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
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                ("customer_name", models.CharField(max_length=150)),
                ("customer_phone", models.CharField(max_length=32)),
                ("note", models.TextField(blank=True)),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="appointments",
                        to="therapist_panel.therapist",
                    ),
                ),
                (
                    "treatment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="appointments",
                        to="therapist_panel.therapisttreatment",
                    ),
                ),
            ],
            options={
                "ordering": ["start_time"],
                "verbose_name": "Appointment",
                "verbose_name_plural": "Appointments",
                "db_table": "appoinments",
            },
        ),
        migrations.AddConstraint(  # enforce logical time ordering
            model_name="appointment",
            constraint=models.CheckConstraint(
                check=Q(end_time__gt=F("start_time")),
                name="appointments_end_after_start",
            ),
        ),
    ]
