# Generated by Django 4.2.20 on 2025-03-31 01:21

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tutor", "0006_tokiponaphrase_quizattempt_listeningexerciseprogress_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="conversation",
            options={"ordering": ["-updated_at"]},
        ),
        migrations.AlterModelOptions(
            name="message",
            options={"ordering": ["created_at"]},
        ),
    ]
