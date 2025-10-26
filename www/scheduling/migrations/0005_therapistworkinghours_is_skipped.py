from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0004_therapistworkinghours"),
    ]

    operations = [
        migrations.AddField(
            model_name="therapistworkinghours",
            name="is_skipped",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="therapistworkinghours",
            index=models.Index(
                fields=["therapist", "is_skipped"],
                name="scheduling_workinghours_therapist_is_skipped_idx",
            ),
        ),
    ]
