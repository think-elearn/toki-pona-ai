from django.contrib import admin
from .models import Glyph, GlyphPracticeProgress


@admin.register(Glyph)
class GlyphAdmin(admin.ModelAdmin):
    list_display = ("name", "meaning", "difficulty", "category")
    list_filter = ("difficulty", "category")
    search_fields = ("name", "meaning", "description")
    fieldsets = (
        (None, {"fields": ("name", "meaning", "image", "reference_image")}),
        (
            "Details",
            {"fields": ("description", "example_sentence", "difficulty", "category")},
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(GlyphPracticeProgress)
class GlyphPracticeProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "glyph",
        "attempts",
        "successful_attempts",
        "accuracy",
        "mastered",
        "last_practiced",
    )
    list_filter = ("mastered", "last_practiced")
    search_fields = ("user__username", "glyph__name")
    readonly_fields = ("accuracy",)
