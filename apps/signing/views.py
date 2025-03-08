from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import SignReference
import json


@login_required
def index(request):
    signs = SignReference.objects.all()
    return render(request, "signing/index.html", {"signs": signs})


@login_required
def practice(request, pk):
    sign = get_object_or_404(SignReference, pk=pk)
    return render(request, "signing/practice.html", {"sign": sign})


@login_required
def analyze_sign(request):
    if request.method == "POST":
        # This is a simplified version - in the actual implementation,
        # you would process the video frames and compare them to the reference
        data = json.loads(request.body)
        data.get("sign_id")
        data.get("landmarks", [])

        # Mock analysis result (would be replaced with actual analysis)
        result = {
            "similarity_score": 85,  # Example score
            "feedback": "Your sign looks good! Pay attention to your hand position.",
            "areas_for_improvement": ["Hand position", "Movement speed"],
        }

        return JsonResponse(result)

    return JsonResponse({"error": "Invalid request"}, status=400)
