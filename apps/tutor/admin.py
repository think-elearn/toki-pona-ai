from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Conversation,
    LearningProgress,
    ListeningExerciseProgress,
    Message,
    QuizAttempt,
    TokiPonaPhrase,
    Transcript,
    VideoResource,
)


@admin.register(TokiPonaPhrase)
class TokiPonaPhraseAdmin(admin.ModelAdmin):
    list_display = ("title", "text", "difficulty", "created_at")
    list_filter = ("difficulty", "created_at")
    search_fields = ("title", "text", "transcript")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("title", "text", "translations", "difficulty")}),
        ("Media", {"fields": ("audio_file", "youtube_video_id")}),
        ("Content", {"fields": ("transcript",)}),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(ListeningExerciseProgress)
class ListeningExerciseProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phrase",
        "completed",
        "correct_attempts",
        "total_attempts",
        "accuracy",
        "last_attempt",
    )
    list_filter = ("completed", "last_attempt")
    search_fields = ("user__username", "phrase__title")
    readonly_fields = ("accuracy",)


class MessageInline(admin.TabularInline):
    model = Message
    fields = ("role", "content", "is_tool_call", "tool_name", "created_at")
    readonly_fields = ("created_at",)
    extra = 0
    max_num = 10
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "created_at",
        "updated_at",
        "is_active",
        "message_count",
    )
    list_filter = ("is_active", "created_at", "updated_at")
    search_fields = ("title", "user__username")
    readonly_fields = ("created_at", "updated_at", "message_count")
    inlines = [MessageInline]
    fieldsets = (
        (None, {"fields": ("title", "user", "is_active", "learning_focus")}),
        ("Metadata", {"fields": ("created_at", "updated_at", "message_count")}),
        ("State", {"fields": ("state",), "classes": ("collapse",)}),
    )

    @admin.display(description="Messages")
    def message_count(self, obj):
        return obj.messages.count()


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation_link",
        "role",
        "short_content",
        "is_tool_call",
        "created_at",
    )
    list_filter = ("role", "is_tool_call", "created_at")
    search_fields = ("content", "conversation__title", "tool_name")
    readonly_fields = ("created_at",)

    @admin.display(description="Content")
    def short_content(self, obj):
        if len(obj.content) > 50:
            return obj.content[:50] + "..."
        return obj.content

    @admin.display(description="Conversation")
    def conversation_link(self, obj):
        url = f"/admin/listening/conversation/{obj.conversation.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.conversation.title)


class TranscriptInline(admin.StackedInline):
    model = Transcript
    fields = ("content", "language", "is_generated", "has_embeddings")
    extra = 0
    max_num = 1
    can_delete = False


@admin.register(VideoResource)
class VideoResourceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "youtube_id",
        "channel",
        "duration",
        "difficulty",
        "has_transcript",
        "created_at",
    )
    list_filter = ("difficulty", "created_at")
    search_fields = ("title", "youtube_id", "channel", "description")
    readonly_fields = ("created_at", "updated_at", "youtube_embed")
    inlines = [TranscriptInline]

    @admin.display(
        description="Has Transcript",
        boolean=True,
    )
    def has_transcript(self, obj):
        return hasattr(obj, "transcript")

    @admin.display(description="YouTube Video")
    def youtube_embed(self, obj):
        youtube_id = obj.youtube_id
        embed_url = f"https://www.youtube.com/embed/{youtube_id}"
        return format_html(
            '<iframe width="560" height="315" src="{}" frameborder="0" '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
            'gyroscope; picture-in-picture" allowfullscreen></iframe>',
            embed_url,
        )


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ("video_title", "language", "is_generated", "has_embeddings")
    list_filter = ("language", "is_generated", "has_embeddings")
    search_fields = ("video__title", "content")
    readonly_fields = ("segments_count", "vocabulary_count")

    @admin.display(description="Video")
    def video_title(self, obj):
        return obj.video.title

    @admin.display(description="Segments Count")
    def segments_count(self, obj):
        return len(obj.segments) if obj.segments else 0

    @admin.display(description="Vocabulary Count")
    def vocabulary_count(self, obj):
        return len(obj.vocabulary) if obj.vocabulary else 0


@admin.register(LearningProgress)
class LearningProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "videos_watched",
        "quizzes_completed",
        "vocabulary_count",
        "last_activity",
    )
    search_fields = ("user__username",)
    readonly_fields = ("last_activity",)

    @admin.display(description="Known Words")
    def vocabulary_count(self, obj):
        return len(obj.known_vocabulary)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "conversation_link",
        "score",
        "correct_count",
        "question_count",
        "difficulty",
        "completed_at",
    )
    list_filter = ("difficulty", "created_at", "completed_at")
    search_fields = ("user__username", "conversation__title")
    readonly_fields = ("created_at", "completed_at", "correct_count", "is_passing")

    @admin.display(description="Conversation")
    def conversation_link(self, obj):
        url = f"/admin/listening/conversation/{obj.conversation.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.conversation.title)

    @admin.display(description="Correct Answers")
    def correct_count(self, obj):
        return obj.correct_count

    @admin.display(description="Total Questions")
    def question_count(self, obj):
        return len(obj.questions)
