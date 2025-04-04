# apps/listening/admin.py
from django.contrib import admin

from .models import ListeningExerciseProgress, TokiPonaPhrase


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
