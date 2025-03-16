from django.contrib.auth.models import User
from django.db import models


class SignReference(models.Model):
    class DifficultyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    name = models.CharField(max_length=50)
    meaning = models.CharField(max_length=100)
    video = models.FileField(upload_to="signs/", null=True, blank=True)
    thumbnail = models.ImageField(upload_to="signs/thumbnails/", null=True, blank=True)
    description = models.TextField(blank=True)
    example_sentence = models.CharField(max_length=200, blank=True)
    landmarks = models.JSONField(null=True, blank=True)  # Store MediaPipe landmarks
    difficulty = models.CharField(
        max_length=20, choices=DifficultyLevel.choices, default=DifficultyLevel.BEGINNER
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SigningProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sign = models.ForeignKey(SignReference, on_delete=models.CASCADE)
    attempts = models.PositiveIntegerField(default=0)
    successful_attempts = models.PositiveIntegerField(default=0)
    last_practiced = models.DateTimeField(auto_now=True)
    mastered = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "sign")
        verbose_name_plural = "Signing progress"

    def __str__(self):
        return f"{self.user.username}'s progress on '{self.sign.name}'"

    @property
    def accuracy(self):
        """Calculate accuracy percentage."""
        if self.attempts == 0:
            return 0
        return int((self.successful_attempts / self.attempts) * 100)
