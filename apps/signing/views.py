from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import SignReference, SigningProgress
import json


@login_required
def index(request):
    """Display a list of signs organized by difficulty."""
    # Get signs grouped by difficulty
    beginner_signs = SignReference.objects.filter(
        difficulty=SignReference.DifficultyLevel.BEGINNER
    )
    intermediate_signs = SignReference.objects.filter(
        difficulty=SignReference.DifficultyLevel.INTERMEDIATE
    )
    advanced_signs = SignReference.objects.filter(
        difficulty=SignReference.DifficultyLevel.ADVANCED
    )

    # Get user progress if any exists
    user_progress = {}
    if request.user.is_authenticated:
        progress_items = SigningProgress.objects.filter(user=request.user)
        for item in progress_items:
            user_progress[item.sign.id] = {
                "accuracy": item.accuracy,
                "attempts": item.attempts,
                "mastered": item.mastered,
            }

    context = {
        "beginner_signs": beginner_signs,
        "intermediate_signs": intermediate_signs,
        "advanced_signs": advanced_signs,
        "user_progress": user_progress,
    }

    return render(request, "signing/index.html", context)


@login_required
def practice(request, pk):
    """Display practice page for a specific sign."""
    sign = get_object_or_404(SignReference, pk=pk)

    # Get or create user progress record
    progress, created = SigningProgress.objects.get_or_create(
        user=request.user, sign=sign
    )

    context = {
        "sign": sign,
        "progress": progress,
    }

    return render(request, "signing/practice.html", context)


@login_required
def analyze_sign(request):
    """Process and evaluate a user's sign attempt."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            sign_id = data.get("sign_id")
            data.get("landmarks", [])

            sign = get_object_or_404(SignReference, pk=sign_id)

            # For MVP, we'll use a simplified approach with random success
            # In a real implementation, we would:
            # 1. Compare user's landmarks with reference landmarks
            # 2. Calculate similarity score
            # 3. Determine if the attempt is successful

            import random

            similarity_score = random.randint(65, 95)  # Random score between 65-95%
            is_successful = similarity_score >= 80

            # Update user progress
            progress, created = SigningProgress.objects.get_or_create(
                user=request.user, sign=sign
            )

            progress.attempts += 1
            if is_successful:
                progress.successful_attempts += 1

                # Mark as mastered if they've succeeded at least 3 times
                # with >70% accuracy
                if progress.successful_attempts >= 3 and progress.accuracy >= 70:
                    progress.mastered = True

            progress.save()

            # Generate appropriate feedback
            if similarity_score >= 90:
                feedback = "Excellent! Your sign is very accurate."
            elif similarity_score >= 80:
                feedback = "Good job! Your sign is recognizable."
            elif similarity_score >= 70:
                feedback = "Getting better. Focus on the hand position and movement."
            else:
                feedback = "Keep practicing. Watch the reference video carefully."

            # Generate areas for improvement based on the sign
            areas_for_improvement = []
            if similarity_score < 90:
                if random.random() > 0.5:
                    areas_for_improvement.append("Hand position")
                if random.random() > 0.5:
                    areas_for_improvement.append("Movement speed")
                if random.random() > 0.5:
                    areas_for_improvement.append("Gesture fluidity")
                if not areas_for_improvement:
                    areas_for_improvement.append("Overall form")

            return JsonResponse(
                {
                    "similarity_score": similarity_score,
                    "feedback": feedback,
                    "is_successful": is_successful,
                    "areas_for_improvement": areas_for_improvement,
                    "attempts": progress.attempts,
                    "successful_attempts": progress.successful_attempts,
                    "accuracy": progress.accuracy,
                    "mastered": progress.mastered,
                }
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)
