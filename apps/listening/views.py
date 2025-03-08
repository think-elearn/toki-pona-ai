from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import TokiPonaPhrase


@login_required
def index(request):
    phrases = TokiPonaPhrase.objects.all()
    return render(request, "listening/index.html", {"phrases": phrases})


@login_required
def exercise(request, pk):
    phrase = get_object_or_404(TokiPonaPhrase, pk=pk)
    return render(request, "listening/exercise.html", {"phrase": phrase})


@login_required
def check_translation(request):
    if request.method == "POST" and request.headers.get("HX-Request"):
        phrase_id = request.POST.get("phrase_id")
        translation = request.POST.get("translation", "").strip().lower()

        phrase = get_object_or_404(TokiPonaPhrase, pk=phrase_id)
        valid_translations = [t.lower() for t in phrase.translations]

        if translation in valid_translations:
            is_correct = True
            feedback = "Correct! Well done."
        else:
            is_correct = False
            feedback = "Not quite right. Try again."

        return render(
            request,
            "listening/partials/feedback.html",
            {
                "is_correct": is_correct,
                "feedback": feedback,
                "correct_translations": phrase.translations,
            },
        )

    return JsonResponse({"error": "Invalid request"}, status=400)
