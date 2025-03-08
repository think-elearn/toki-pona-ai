from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Glyph
import json


@login_required
def index(request):
    glyphs = Glyph.objects.all()
    return render(request, "writing/index.html", {"glyphs": glyphs})


@login_required
def practice(request, glyph_name):
    glyph = get_object_or_404(Glyph, name=glyph_name)
    return render(request, "writing/practice.html", {"glyph": glyph})


@login_required
def check_drawing(request):
    if request.method == "POST":
        # This is a simplified version - in the actual implementation,
        # you would process the drawing and compare it to the template
        data = json.loads(request.body)
        data.get("glyph_name")
        data.get("image_data", "").split(",")[1]

        # Basic feedback (would be replaced with actual recognition logic)
        feedback = {
            "is_correct": True,  # To be determined by the recognition algorithm
            "confidence": 0.85,  # Example confidence score
            "feedback": "Your drawing looks good!",
        }

        return JsonResponse(feedback)

    return JsonResponse({"error": "Invalid request"}, status=400)
