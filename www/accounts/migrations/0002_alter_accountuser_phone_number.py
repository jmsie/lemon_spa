"""Allow AccountUser.phone_number to be optional for special cases like admin accounts."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accountuser",
            name="phone_number",
            field=models.CharField(
                blank=True,
                help_text="Normalized phone number stored in E.164 format.",
                max_length=32,
                null=True,
                unique=True,
            ),
        ),
    ]
