"""Link questionnaires to appointments."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0001_initial"),
        ("questionnaires", "0002_service_questionnaire_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="questionnaire",
            name="appointment",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="questionnaire",
                to="appointments.appointment",
                verbose_name="預約",
            ),
        ),
    ]
