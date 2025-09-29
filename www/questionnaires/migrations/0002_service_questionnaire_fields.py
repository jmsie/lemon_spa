"""Update questionnaire fields for service survey details."""

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("questionnaires", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="questionnaire",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "服務問卷",
                "verbose_name_plural": "服務問卷",
            },
        ),
        migrations.RemoveField(
            model_name="questionnaire",
            name="description",
        ),
        migrations.RemoveField(
            model_name="questionnaire",
            name="title",
        ),
        migrations.RemoveField(
            model_name="questionnaire",
            name="updated_at",
        ),
        migrations.AlterField(
            model_name="questionnaire",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name="填寫時間",
            ),
        ),
        migrations.AlterField(
            model_name="questionnaire",
            name="therapist",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="service_surveys",
                to="therapist_panel.therapist",
            ),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="comment",
            field=models.TextField(blank=True, verbose_name="備註"),
        ),
        migrations.AddField(
            model_name="questionnaire",
            name="rating",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "1 星"), (2, "2 星"), (3, "3 星"), (4, "4 星"), (5, "5 星")],
                default=5,
                verbose_name="星級",
            ),
        ),
    ]
