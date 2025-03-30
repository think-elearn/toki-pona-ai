from django.contrib.auth.models import User
from django.db import models
from pgvector.django import HnswIndex, VectorField


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    learning_focus = models.CharField(max_length=50, null=True, blank=True)
    # Metadata about conversation state
    state = models.JSONField(default=dict, blank=True)


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
