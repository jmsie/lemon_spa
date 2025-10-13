"""Initial migration for phone verification app."""

from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Create phone verification and audit log tables."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PhoneVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number", models.CharField(max_length=32, unique=True)),
                ("code_hash", models.CharField(max_length=128)),
                ("expires_at", models.DateTimeField()),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("send_count", models.PositiveSmallIntegerField(default=0)),
                ("last_sent_at", models.DateTimeField(blank=True, null=True)),
                ("is_verified", models.BooleanField(default=False)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Phone Verification",
                "verbose_name_plural": "Phone Verifications",
            },
        ),
        migrations.CreateModel(
            name="PhoneVerificationAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number", models.CharField(max_length=32)),
                ("event_type", models.CharField(
                    choices=[
                        ("send", "Code sent"),
                        ("resend_blocked", "Resend blocked"),
                        ("code_verified", "Code verified"),
                        ("code_invalid", "Invalid code submitted"),
                        ("code_expired", "Expired code submitted"),
                        ("attempts_exceeded", "Maximum attempts exceeded"),
                    ],
                    max_length=32,
                )),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("verification", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="audit_logs",
                    to="phone_verification.phoneverification",
                )),
            ],
            options={
                "verbose_name": "Phone Verification Audit Log",
                "verbose_name_plural": "Phone Verification Audit Logs",
            },
        ),
        migrations.AddIndex(
            model_name="phoneverification",
            index=models.Index(fields=["phone_number"], name="phone_veri_phone_nu_e92ab4_idx"),
        ),
        migrations.AddIndex(
            model_name="phoneverification",
            index=models.Index(fields=["is_verified", "expires_at"], name="phone_veri_is_veri_326a8c_idx"),
        ),
        migrations.AddIndex(
            model_name="phoneverificationauditlog",
            index=models.Index(fields=["phone_number", "event_type"], name="phone_veri_phone_nu_a20608_idx"),
        ),
        migrations.AddIndex(
            model_name="phoneverificationauditlog",
            index=models.Index(fields=["created_at"], name="phone_veri_created__fa9414_idx"),
        ),
    ]
