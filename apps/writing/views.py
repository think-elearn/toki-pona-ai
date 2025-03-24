import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import Glyph, GlyphPracticeProgress
from .services import character_recognition, svg_service

logger = logging.getLogger(__name__)


@login_required
def index(request):
    """Display glyphs organized by difficulty and category."""
    # Get all glyphs
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

    # Get SVG URLs for all glyphs
    glyph_svg_urls = {}
    for glyph in (
        list(beginner_glyphs) + list(intermediate_glyphs) + list(advanced_glyphs)
    ):
        svg_url = svg_service.get_svg_url(glyph.name)
        glyph_svg_urls[glyph.id] = svg_url

    context = {
        "beginner_glyphs": beginner_glyphs,
        "intermediate_glyphs": intermediate_glyphs,
        "advanced_glyphs": advanced_glyphs,
        "user_progress": user_progress,
        "svg_urls": glyph_svg_urls,
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

    # Get SVG URL for the glyph
    svg_url = svg_service.get_svg_url(glyph.name)

    context = {
        "glyph": glyph,
        "progress": progress,
        "recent_accuracy": progress.accuracy,
        "svg_url": svg_url,
    }

    return render(request, "writing/practice.html", context)


@login_required
def check_drawing(request):
    """Process and evaluate a user's glyph drawing."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            glyph_name = data.get("glyph_name")
            image_data = data.get("image_data", "")

            # Get the glyph from database
            glyph = get_object_or_404(Glyph, name=glyph_name)

            # Call the character recognition service
            character, similarity, debug_info = character_recognition.recognize_base64(
                image_data,
                threshold=0.7,  # Configurable threshold
            )

            # Round similarity score to percentage
            similarity_percentage = round(similarity * 100)
            is_correct = similarity >= 0.7 and character == glyph_name

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
            if similarity >= 0.90:
                feedback = "Excellent! Your glyph looks great."
            elif similarity >= 0.80:
                feedback = "Good job! Your glyph is recognizable."
            elif similarity >= 0.70:
                feedback = "Getting better. Try to make your strokes more precise."
            else:
                feedback = "Keep practicing. Focus on the overall shape of the glyph."

            # Return results as JSON
            return JsonResponse(
                {
                    "is_correct": is_correct,
                    "similarity": similarity_percentage,
                    "feedback": feedback,
                    "debug_info": debug_info if settings.DEBUG else {},
                    "attempts": progress.attempts,
                    "successful_attempts": progress.successful_attempts,
                    "accuracy": progress.accuracy,
                    "mastered": progress.mastered,
                }
            )

        except Exception as e:
            logger.error(f"Error in check_drawing: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def get_svg_content(request, glyph_name):
    """Get SVG content for a specific glyph."""
    try:
        svg_content = svg_service.get_svg_content(glyph_name)
        if svg_content:
            return JsonResponse({"svg_content": svg_content})
        else:
            return JsonResponse({"error": "SVG not found"}, status=404)
    except Exception as e:
        logger.error(f"Error getting SVG content: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
