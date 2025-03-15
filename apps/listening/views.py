from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.template.loader import render_to_string

from .models import ListeningExerciseProgress, TokiPonaPhrase
from .services import TranslationService, TranscriptService


@login_required
def index(request):
    """Display a list of available Toki Pona phrases grouped by difficulty."""
    # Get phrases grouped by difficulty
    beginner_phrases = TokiPonaPhrase.objects.filter(
        difficulty=TokiPonaPhrase.DifficultyLevel.BEGINNER
    )
    intermediate_phrases = TokiPonaPhrase.objects.filter(
        difficulty=TokiPonaPhrase.DifficultyLevel.INTERMEDIATE
    )
    advanced_phrases = TokiPonaPhrase.objects.filter(
        difficulty=TokiPonaPhrase.DifficultyLevel.ADVANCED
    )

    context = {
        "beginner_phrases": beginner_phrases,
        "intermediate_phrases": intermediate_phrases,
        "advanced_phrases": advanced_phrases,
    }

    return render(request, "listening/index.html", context)


@login_required
def exercise(request, pk):
    """Display a specific Toki Pona exercise with audio and transcript."""
    phrase = get_object_or_404(TokiPonaPhrase, pk=pk)

    # Parse the transcript if available
    parsed_transcript = None
    if phrase.transcript:
        parsed_transcript = TranscriptService.parse_transcript(phrase.transcript)

    context = {
        "phrase": phrase,
        "parsed_transcript": parsed_transcript,
    }

    return render(request, "listening/exercise.html", context)


@login_required
def check_translation(request):
    """HTMX endpoint to check a submitted translation."""
    if request.method == "POST" and request.headers.get("HX-Request"):
        phrase_id = request.POST.get("phrase_id")
        translation = request.POST.get("translation", "").strip()

        if not phrase_id or not translation:
            return HttpResponseBadRequest("Missing required parameters")

        # Validate the translation using the service
        translation_service = TranslationService()
        result = translation_service.validate_translation(phrase_id, translation)

        # Update progress tracking
        phrase = get_object_or_404(TokiPonaPhrase, pk=phrase_id)
        progress, created = ListeningExerciseProgress.objects.get_or_create(
            user=request.user, phrase=phrase
        )
        progress.total_attempts += 1
        if result["is_correct"]:
            progress.correct_attempts += 1
            progress.completed = True
        progress.save()

        # Render the feedback template with the result
        html = render_to_string(
            "listening/partials/feedback.html",
            {
                "is_correct": result["is_correct"],
                "feedback": result["feedback"],
                "correct_translations": result.get("correct_translations", []),
                "phrase_id": phrase_id,
                "progress": progress,
            },
            request=request,
        )

        return JsonResponse(
            {
                "html": html,
                "is_correct": result["is_correct"],
            }
        )

    return HttpResponseBadRequest("Invalid request")
