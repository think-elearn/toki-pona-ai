import json
import logging

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
        progress_entries = GlyphPracticeProgress.objects.filter(user=request.user)
        user_progress = {
            entry.glyph.id: {
                "mastered": entry.mastered,
                "attempts": entry.attempts,
                "accuracy": round(entry.successful_attempts / entry.attempts * 100, 2)
                if entry.attempts > 0
                else 0,
            }
            for entry in progress_entries
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
        "debug": request.user.is_staff,  # Enable debugging for staff users
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

            # Call the character recognition service with lower threshold for better results
            character, similarity, recognition_debug_info = (
                character_recognition.recognize_base64(
                    image_data,
                    threshold=0.6,  # Lower threshold for more lenient matching
                )
            )

            # Apply a slight boost to similarity score (empirically tuned)
            # This helps account for the inherent differences between user drawings and templates
            adjusted_similarity = min(
                1.0, similarity * 1.15
            )  # 15% boost, capped at 1.0

            # Round similarity score to percentage
            similarity_percentage = round(adjusted_similarity * 100)
            is_correct = adjusted_similarity >= 0.65 and character == glyph_name

            # Comprehensive debugging info
            debug_info = {
                "glyph_name": glyph_name,
                "glyph_id": glyph.id,
                "has_image": bool(glyph.image),
                "image_url": glyph.image.url if glyph.image else None,
                "recognition": {
                    "raw_similarity": round(similarity * 100),
                    "adjusted_similarity": similarity_percentage,
                    "raw_threshold": 0.6,
                    "effective_threshold": 0.65,
                    "recognized_as": character,
                    "is_match": character == glyph_name,
                },
                "scores": recognition_debug_info.get("scores", {}),
            }

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

            # Generate feedback based on adjusted score with more encouraging feedback
            if adjusted_similarity >= 0.85:
                feedback = "Excellent! Your glyph looks great."
            elif adjusted_similarity >= 0.75:
                feedback = "Good job! Your glyph is clearly recognizable."
            elif adjusted_similarity >= 0.65:
                feedback = "Well done! Keep practicing to perfect your strokes."
            elif adjusted_similarity >= 0.55:
                feedback = "Getting better. Try to make your strokes more precise."
            elif adjusted_similarity >= 0.45:
                feedback = "Not bad. Keep practicing to improve your accuracy."
            else:
                feedback = "Keep practicing. Focus on the overall shape of the glyph."

            # Return results
            return JsonResponse(
                {
                    "is_correct": bool(is_correct),
                    "similarity": similarity_percentage,
                    "feedback": str(feedback),
                    "debug_info": debug_info,
                    "attempts": int(progress.attempts),
                    "successful_attempts": int(progress.successful_attempts),
                    "accuracy": int(progress.accuracy),
                    "mastered": bool(progress.mastered),
                }
            )

        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()

            return JsonResponse(
                {
                    "error": str(e),
                    "traceback": error_traceback,
                    "is_correct": False,
                    "similarity": 0,
                    "debug_info": {"error": str(e), "traceback": error_traceback},
                    "attempts": 0,
                    "successful_attempts": 0,
                    "accuracy": 0,
                    "mastered": False,
                }
            )

    return JsonResponse({"error": "Invalid request method"}, status=400)


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
