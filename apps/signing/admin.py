from django.contrib import admin
from .models import SignReference, SigningProgress


@admin.register(SignReference)
class SignReferenceAdmin(admin.ModelAdmin):
    list_display = ("name", "meaning", "difficulty", "created_at")
    list_filter = ("difficulty", "created_at")
    search_fields = ("name", "meaning", "description")
    fieldsets = (
        (None, {"fields": ("name", "meaning", "video", "thumbnail")}),
        (
            "Details",
            {"fields": ("description", "example_sentence", "difficulty", "landmarks")},
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(SigningProgress)
class SigningProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "sign",
        "attempts",
        "successful_attempts",
        "accuracy",
        "mastered",
        "last_practiced",
    )
    list_filter = ("mastered", "last_practiced")
    search_fields = ("user__username", "sign__name")
    readonly_fields = ("accuracy",)
