from django.db import models


class DifficultyLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"


class TokiPonaPhrase(models.Model):
    title = models.CharField(max_length=100, default="Toki Pona Exercise")
    text = models.CharField(max_length=200)
    translations = models.JSONField()
    audio_file = models.FileField(upload_to="audio/", null=True, blank=True)
    youtube_video_id = models.CharField(max_length=20, null=True, blank=True)
    transcript = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.BEGINNER,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
