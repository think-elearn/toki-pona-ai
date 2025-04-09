# Generated manually for pgvector removal documentation

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tutor", "0008_alter_message_role"),
    ]

    operations = [
        # This migration is just for documentation purposes
        # The actual embeddings field was removed from the model in a previous commit
        # We've modified 0004_transcript.py directly to exclude pgvector fields
    ]
