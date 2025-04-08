from django.contrib.auth.models import User
from django.db import models
from pgvector.django import HnswIndex, VectorField


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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    phrase = models.ForeignKey(TokiPonaPhrase, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    last_attempt = models.DateTimeField(auto_now=True)
    correct_attempts = models.PositiveIntegerField(default=0)
    total_attempts = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "phrase"], name="unique_user_phrase"
            )
        ]
        verbose_name_plural = "Listening exercise progress"

    def __str__(self):
        return f"{self.user.username}'s progress on '{self.phrase.title}'"

    @property
    def accuracy(self):
        """Calculate accuracy percentage."""
        if self.total_attempts == 0:
            return 0
        return (self.correct_attempts / self.total_attempts) * 100


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    learning_focus = models.CharField(max_length=50, null=True, blank=True)
    # Metadata about conversation state
    state = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class Message(models.Model):
    class MessageRole(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    conversation = models.ForeignKey(
        Conversation, related_name="messages", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=10, choices=MessageRole.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # For tool use tracking
    is_tool_call = models.BooleanField(default=False)
    tool_name = models.CharField(max_length=50, null=True, blank=True)
    tool_input = models.JSONField(null=True, blank=True)
    tool_output = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} message in {self.conversation.title}"


class VideoResource(models.Model):
    class DifficultyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    youtube_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    channel = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration = models.CharField(max_length=20)  # Format: MM:SS
    thumbnail_url = models.URLField()
    published_at = models.DateTimeField()
    view_count = models.IntegerField(default=0)

    # Categorization
    difficulty = models.CharField(
        max_length=20, choices=DifficultyLevel.choices, default=DifficultyLevel.BEGINNER
    )
    topics = models.JSONField(default=list, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.youtube_id})"


class Transcript(models.Model):
    video = models.OneToOneField(
        VideoResource, on_delete=models.CASCADE, related_name="transcript"
    )
    content = models.TextField()
    language = models.CharField(max_length=10, default="en")
    is_generated = models.BooleanField(default=False)
    has_embeddings = models.BooleanField(default=False)
    embeddings = VectorField(
        dimensions=1536, null=True
    )  # For storing vector embeddings

    # Store processed segments for easy retrieval
    segments = models.JSONField(default=list)
    vocabulary = models.JSONField(default=list)  # Extracted Toki Pona vocabulary

    class Meta:
        indexes = [
            # Standard index for the foreign key
            models.Index(fields=["video"]),
            # HNSW index for faster approximate nearest neighbor search
            # Better than IVFFlat for production with read-heavy workloads
            HnswIndex(
                name="transcript_embeddings_hnsw_idx",
                fields=["embeddings"],
                m=16,  # Number of connections per element
                ef_construction=64,  # Size of dynamic candidate list for construction
                opclasses=[
                    "vector_cosine_ops"
                ],  # Cosine distance is often best for text embeddings
            ),
        ]

    def __str__(self):
        return f"Transcript for {self.video.title}"


class LearningProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Overall stats
    videos_watched = models.PositiveIntegerField(default=0)
    quizzes_completed = models.PositiveIntegerField(default=0)
    conversations_count = models.PositiveIntegerField(default=0)

    # Vocabulary progress
    known_vocabulary = models.JSONField(default=list)
    vocabulary_strength = models.JSONField(default=dict)  # Word -> strength mapping

    # Skill levels
    listening_level = models.FloatField(default=0.0)  # 0-10 scale
    translation_level = models.FloatField(default=0.0)
    grammar_level = models.FloatField(default=0.0)

    # Learning profile
    interests = models.JSONField(default=list)
    learning_style = models.CharField(max_length=50, null=True, blank=True)

    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Learning Progress"


class QuizAttempt(models.Model):
    """Record of a quiz attempt by a user."""

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    video = models.ForeignKey(
        VideoResource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quiz_attempts",
    )

    # Quiz content
    questions = models.JSONField(
        help_text="JSON array of quiz questions with options and correct answers"
    )
    user_answers = models.JSONField(
        help_text="JSON array of user-selected answer indices"
    )
    correct_answers = models.JSONField(
        help_text="JSON array of boolean values indicating correct/incorrect"
    )

    # Results
    score = models.FloatField(
        help_text="Percentage score (0-100)"
    )  # Percentage correct
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Feedback
    feedback = models.TextField(
        blank=True, help_text="Textual feedback provided to the user"
    )
    areas_for_improvement = models.JSONField(
        default=list, help_text="List of areas to focus on for improvement"
    )

    # Quiz metadata
    difficulty = models.CharField(
        max_length=20,
        choices=TokiPonaPhrase.DifficultyLevel.choices,
        default=TokiPonaPhrase.DifficultyLevel.BEGINNER,
        help_text="Difficulty level of the quiz",
    )
    question_count = models.PositiveIntegerField(
        default=5, help_text="Number of questions in the quiz"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Quiz Attempt"
        verbose_name_plural = "Quiz Attempts"

    def __str__(self):
        return f"{self.user.username}'s Quiz ({self.score:.1f}%)"

    @property
    def correct_count(self):
        """Return the number of correct answers."""
        return sum(1 for answer in self.correct_answers if answer)

    @property
    def is_passing(self):
        """Check if the score is passing (>= 70%)."""
        return self.score >= 70.0
