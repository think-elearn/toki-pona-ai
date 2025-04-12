import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import SigningProgress, SignReference
from .services import (
    SignComparer,
    SignVisualizer,
    convert_frames_to_base64,
    load_landmarks_from_model,
)

logger = logging.getLogger(__name__)


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
@require_POST
def analyze_sign(request):
    """Process and evaluate a user's sign attempt."""
    try:
        data = json.loads(request.body)
        sign_id = data.get("sign_id")
        base64_frames = data.get("frames", [])

        if not sign_id or not base64_frames:
            return JsonResponse({"error": "Missing required data"}, status=400)

        sign = get_object_or_404(SignReference, pk=sign_id)

        # Initialize services
        sign_comparer = SignComparer()

        # Get reference landmarks
        reference_landmarks = load_landmarks_from_model(sign)
        if not reference_landmarks:
            return JsonResponse(
                {"error": "No reference landmarks available for this sign"}, status=400
            )

        # Extract landmarks from user's attempt
        learner_landmarks = sign_comparer.extract_landmarks_from_base64_frames(
            base64_frames
        )
        if not learner_landmarks or all(not frame for frame in learner_landmarks):
            return JsonResponse(
                {"error": "Could not detect hand landmarks in your sign"}, status=400
            )

        # Compare signs
        comparison_results = sign_comparer.compare_signs(
            reference_landmarks, learner_landmarks
        )
        feedback = sign_comparer.generate_feedback(comparison_results)

        # Determine if attempt was successful
        similarity_score = comparison_results["similarity_score"]
        is_successful = similarity_score >= 80

        # Update user progress
        progress, created = SigningProgress.objects.get_or_create(
            user=request.user, sign=sign
        )

        progress.attempts += 1
        if is_successful:
            progress.successful_attempts += 1

            # Mark as mastered if they've succeeded at least 3 times with >70% accuracy
            if progress.successful_attempts >= 3 and progress.accuracy >= 70:
                progress.mastered = True

        progress.save()

        # Return results
        return JsonResponse(
            {
                "similarity_score": similarity_score,
                "feedback": feedback["overall_score"],
                "rating": feedback["rating"],
                "is_successful": is_successful,
                "areas_for_improvement": feedback["weak_points"],
                "attempts": progress.attempts,
                "successful_attempts": progress.successful_attempts,
                "accuracy": progress.accuracy,
                "mastered": progress.mastered,
            }
        )

    except Exception as e:
        logger.exception(f"Error analyzing sign: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def track_hands(request):
    """Process a single frame and return hand landmarks for real-time tracking."""
    try:
        data = json.loads(request.body)
        base64_frame = data.get("frame")

        if not base64_frame:
            return JsonResponse({"error": "No frame provided"}, status=400)

        # Initialize services
        sign_comparer = SignComparer()

        # Process single frame
        landmarks = sign_comparer.extract_landmarks_from_base64_frames([base64_frame])

        # Return the landmarks for the frontend to visualize
        return JsonResponse({"landmarks": landmarks[0] if landmarks else []})

    except Exception as e:
        logger.exception(f"Error tracking hands: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def comparison_visualization(request, pk):
    """Generate a comparison visualization between the reference sign and the user's attempt."""
    try:
        sign = get_object_or_404(SignReference, pk=pk)
        attempt_id = request.GET.get("attempt_id")

        if not attempt_id:
            return JsonResponse({"error": "No attempt ID provided"}, status=400)

        # In a real implementation, we would retrieve the user's recorded attempt
        # For now, we'll just compare with the reference

        # Initialize services
        sign_visualizer = SignVisualizer()

        # Mock visualization (in a real app, we'd use stored attempt frames)
        # Just returning the reference visualization for now
        if sign.video:
            # Get frames from the video
            reference_frames = sign_visualizer.process_video_frames(sign.video.path)
            processed_frames, _ = sign_visualizer.extract_frames_with_landmarks(
                reference_frames
            )

            # Convert frames to base64 for the frontend
            base64_frames = convert_frames_to_base64(processed_frames)

            return JsonResponse(
                {"frames": base64_frames, "total_frames": len(base64_frames)}
            )
        else:
            return JsonResponse({"error": "No reference video available"}, status=404)

    except Exception as e:
        logger.exception(f"Error generating comparison visualization: {e}")
        return JsonResponse({"error": str(e)}, status=500)
