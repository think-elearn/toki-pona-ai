from django.contrib.auth.models import User
from django.db import models


class Glyph(models.Model):
    class DifficultyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    class Category(models.TextChoices):
        BASIC = "basic", "Basic Vocabulary"
        COMPOUND = "compound", "Compound Concepts"
        GRAMMAR = "grammar", "Grammatical Particles"

    name = models.CharField(max_length=50)
    meaning = models.CharField(max_length=100)
    image = models.ImageField(upload_to="glyphs/", null=True, blank=True)
    reference_image = models.ImageField(
        upload_to="glyphs/reference/", null=True, blank=True
    )
    description = models.TextField(blank=True)
    example_sentence = models.CharField(max_length=200, blank=True)
    difficulty = models.CharField(
        max_length=20, choices=DifficultyLevel.choices, default=DifficultyLevel.BEGINNER
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.BASIC
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class GlyphPracticeProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    glyph = models.ForeignKey(Glyph, on_delete=models.CASCADE)
    attempts = models.PositiveIntegerField(default=0)
    successful_attempts = models.PositiveIntegerField(default=0)
    last_practiced = models.DateTimeField(auto_now=True)
    mastered = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "glyph")
        verbose_name_plural = "Glyph practice progress"

    def __str__(self):
        return f"{self.user.username}'s progress on '{self.glyph.name}'"

    @property
    def accuracy(self):
        """Calculate accuracy percentage."""
        if self.attempts == 0:
            return 0
        return int((self.successful_attempts / self.attempts) * 100)
