# Generated by Django 4.2.20 on 2025-04-09 09:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tutor", "0007_alter_conversation_options_alter_message_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="message",
            name="role",
            field=models.CharField(
                choices=[("user", "User"), ("assistant", "Assistant")], max_length=10
            ),
        ),
    ]
