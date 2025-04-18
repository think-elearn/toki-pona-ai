# Generated by Django 4.2.20 on 2025-03-30 05:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tutor", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Message",
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
                    "role",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("assistant", "Assistant"),
                            ("system", "System"),
                        ],
                        max_length=10,
                    ),
                ),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_tool_call", models.BooleanField(default=False)),
                ("tool_name", models.CharField(blank=True, max_length=50, null=True)),
                ("tool_input", models.JSONField(blank=True, null=True)),
                ("tool_output", models.JSONField(blank=True, null=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="tutor.conversation",
                    ),
                ),
            ],
        ),
    ]
