# Generated manually to remove pgvector dependency

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tutor", "0003_videoresource"),
    ]

    operations = [
        migrations.CreateModel(
            name="Transcript",
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
                ("content", models.TextField()),
                ("language", models.CharField(default="en", max_length=10)),
                ("is_generated", models.BooleanField(default=False)),
                ("has_embeddings", models.BooleanField(default=False)),
                ("segments", models.JSONField(default=list)),
                ("vocabulary", models.JSONField(default=list)),
                (
                    "video",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transcript",
                        to="tutor.videoresource",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["video"], name="tutor_trans_video_i_2b9d98_idx"
                    ),
                ],
            },
        ),
    ]
