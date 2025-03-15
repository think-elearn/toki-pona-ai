from django.db import models


class TokiPonaPhrase(models.Model):
    class DifficultyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

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


class ListeningExerciseProgress(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    phrase = models.ForeignKey(TokiPonaPhrase, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    last_attempt = models.DateTimeField(auto_now=True)
    correct_attempts = models.PositiveIntegerField(default=0)
    total_attempts = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "phrase")
        verbose_name_plural = "Listening exercise progress"

    def __str__(self):
        return f"{self.user.username}'s progress on '{self.phrase.title}'"

    @property
    def accuracy(self):
        """Calculate accuracy percentage."""
        if self.total_attempts == 0:
            return 0
        return (self.correct_attempts / self.total_attempts) * 100
