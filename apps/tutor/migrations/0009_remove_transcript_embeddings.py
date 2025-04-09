# Generated manually to remove pgvector dependency

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tutor", "0008_alter_message_role"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="transcript",
            name="embeddings",
        ),
    ]
