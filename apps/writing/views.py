import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import Glyph, GlyphPracticeProgress


@login_required
def index(request):
    """Display glyphs organized by difficulty and category."""
    # Get counts of glyphs by difficulty
    beginner_glyphs = Glyph.objects.filter(difficulty=Glyph.DifficultyLevel.BEGINNER)
    intermediate_glyphs = Glyph.objects.filter(
        difficulty=Glyph.DifficultyLevel.INTERMEDIATE
    )
    advanced_glyphs = Glyph.objects.filter(difficulty=Glyph.DifficultyLevel.ADVANCED)

    # Get user progress if any exists
    user_progress = {}
    if request.user.is_authenticated:
        progress_items = GlyphPracticeProgress.objects.filter(user=request.user)
        for item in progress_items:
            user_progress[item.glyph.id] = {
                "accuracy": item.accuracy,
                "attempts": item.attempts,
                "mastered": item.mastered,
            }

    context = {
        "beginner_glyphs": beginner_glyphs,
        "intermediate_glyphs": intermediate_glyphs,
        "advanced_glyphs": advanced_glyphs,
        "user_progress": user_progress,
    }

    return render(request, "writing/index.html", context)


@login_required
def practice(request, glyph_name):
    """Display practice page for a specific glyph."""
    glyph = get_object_or_404(Glyph, name=glyph_name)

    # Get or create user progress record
    progress, created = GlyphPracticeProgress.objects.get_or_create(
        user=request.user, glyph=glyph
    )

    context = {
        "glyph": glyph,
        "progress": progress,
        "recent_accuracy": progress.accuracy,
    }

    return render(request, "writing/practice.html", context)


@login_required
def check_drawing(request):
    """Process and evaluate a user's glyph drawing."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            glyph_name = data.get("glyph_name")
            data.get("image_data", "").split(",")[1]  # Get base64 data

            glyph = get_object_or_404(Glyph, name=glyph_name)

            # In real implementation, we'd analyze the drawing
            # For now, let's simulate a basic recognition system
            # that gives feedback based on random thresholds
            import random

            similarity_score = random.uniform(0.6, 0.95)  # Random score between 60-95%
            is_correct = similarity_score > 0.80

            # Update user progress
            progress, created = GlyphPracticeProgress.objects.get_or_create(
                user=request.user, glyph=glyph
            )

            progress.attempts += 1
            if is_correct:
                progress.successful_attempts += 1

                # Mark as mastered if they've succeeded at least 3 times
                # with >70% accuracy
                if progress.successful_attempts >= 3 and progress.accuracy >= 70:
                    progress.mastered = True

            progress.save()

            # Generate feedback based on score
            if similarity_score > 0.90:
                feedback = "Excellent! Your glyph looks great."
            elif similarity_score > 0.80:
                feedback = "Good job! Your glyph is recognizable."
            elif similarity_score > 0.70:
                feedback = "Getting better. Try to make your strokes more precise."
            else:
                feedback = "Keep practicing. Focus on the overall shape of the glyph."

            return JsonResponse(
                {
                    "is_correct": is_correct,
                    "similarity": round(similarity_score * 100),
                    "feedback": feedback,
                    "attempts": progress.attempts,
                    "successful_attempts": progress.successful_attempts,
                    "accuracy": progress.accuracy,
                    "mastered": progress.mastered,
                }
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)
