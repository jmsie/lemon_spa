"""Initial migration for therapist data."""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Therapist",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_name", models.CharField(max_length=150)),
                ("first_name", models.CharField(max_length=150)),
                ("nickname", models.CharField(max_length=150)),
                ("phone_number", models.CharField(max_length=32)),
                ("address", models.CharField(max_length=255)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["last_name", "first_name"],
            },
        ),
    ]
