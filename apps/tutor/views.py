from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.tutor.services import TranscriptService, TranslationService

from .models import (
    Conversation,
    LearningProgress,
    ListeningExerciseProgress,
    Message,
    QuizAttempt,
    TokiPonaPhrase,
    VideoResource,
)
from .tasks import process_user_message


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

    # Get user's recent conversations
    recent_conversations = Conversation.objects.filter(user=request.user).order_by(
        "-updated_at"
    )[:5]

    context = {
        "beginner_phrases": beginner_phrases,
        "intermediate_phrases": intermediate_phrases,
        "advanced_phrases": advanced_phrases,
        "recent_conversations": recent_conversations,
    }

    return render(request, "tutor/index.html", context)


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

    return render(request, "tutor/practice.html", context)


@login_required
def check_translation(request):
    """HTMX endpoint to check a submitted translation."""
    if request.method == "POST" and request.htmx:
        phrase_id = request.POST.get("phrase_id")
        translation = request.POST.get("translation", "").strip()

        if not phrase_id or not translation:
            return HttpResponseBadRequest("Missing required parameters")

        # Validate the translation using the service
        translation_service = TranslationService()
        result = translation_service.validate_translation(phrase_id, translation)

        # Get the phrase for context
        phrase = get_object_or_404(TokiPonaPhrase, pk=phrase_id)

        # Update progress tracking
        progress, created = ListeningExerciseProgress.objects.get_or_create(
            user=request.user, phrase=phrase
        )
        progress.total_attempts += 1
        if result["is_correct"]:
            progress.correct_attempts += 1
            progress.completed = True
        progress.save()

        # Render the feedback template directly
        context = {
            "is_correct": result["is_correct"],
            "feedback": result["feedback"],
            "correct_translations": result.get("correct_translations", []),
            "phrase_id": phrase_id,
            "phrase": phrase,
            "progress": progress,
        }

        # Return the rendered HTML directly, not as JSON
        return render(request, "tutor/partials/feedback.html", context)

    return HttpResponseBadRequest("Invalid request")


@login_required
def conversation_list(request):
    """Display a list of user's conversations."""
    conversations = Conversation.objects.filter(user=request.user).order_by(
        "-updated_at"
    )

    return render(
        request, "tutor/conversation_list.html", {"conversations": conversations}
    )


@login_required
def create_conversation(request):
    """Create a new conversation."""
    if request.method == "POST":
        title = request.POST.get("title", "New Conversation")

        conversation = Conversation.objects.create(
            user=request.user,
            title=title,
            state={},  # Empty initial state
        )

        # Add system welcome message
        Message.objects.create(
            conversation=conversation,
            role="system",
            content="Welcome to your Toki Pona learning session! How can I help you today?",
        )

        return redirect("tutor:conversation", conversation_id=conversation.id)

    # If GET request, show the creation form
    return render(request, "tutor/create_conversation.html")


@login_required
def conversation_view(request, conversation_id):
    """Display a specific conversation with chat interface."""
    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )

    # Get user progress
    user_progress, created = LearningProgress.objects.get_or_create(user=request.user)

    # Calculate percentages for progress bars
    vocabulary_percent = min(100, len(user_progress.known_vocabulary) / 120 * 100)
    grammar_percent = min(100, user_progress.grammar_level * 10)
    listening_percent = min(100, user_progress.listening_level * 10)

    # Format progress for template
    progress_data = {
        "vocabulary_percent": round(vocabulary_percent),
        "grammar_percent": round(grammar_percent),
        "listening_percent": round(listening_percent),
    }

    # Get current video if available
    current_video = None
    if conversation.state and conversation.state.get("current_video_id"):
        video_id = conversation.state["current_video_id"]
        try:
            video = VideoResource.objects.get(youtube_id=video_id)
            current_video = {
                "video_id": video.youtube_id,
                "title": video.title,
                "channel": video.channel,
                "duration": video.duration,
                "transcript": video.transcript.content
                if hasattr(video, "transcript")
                else "",
            }

            # Add segments if available
            if hasattr(video, "transcript") and video.transcript.segments:
                current_video["segments"] = video.transcript.segments

            # Add vocabulary if available
            if conversation.state.get("vocabulary"):
                current_video["vocabulary"] = conversation.state["vocabulary"]
            elif hasattr(video, "transcript") and video.transcript.vocabulary:
                current_video["vocabulary"] = video.transcript.vocabulary
        except VideoResource.DoesNotExist:
            pass

    # Get current quiz if available
    current_quiz = None
    if conversation.state and conversation.state.get("current_quiz"):
        current_quiz = conversation.state["current_quiz"]

        # Check if there's a quiz attempt
        quiz_attempt = QuizAttempt.objects.filter(
            conversation=conversation, user=request.user, completed_at__isnull=False
        ).first()

        if quiz_attempt:
            current_quiz["quiz_attempt"] = {
                "id": quiz_attempt.id,
                "score": quiz_attempt.score,
                "correct_count": quiz_attempt.correct_answers.count(True),
                "user_answers": quiz_attempt.user_answers,
                "completed_at": quiz_attempt.completed_at,
            }

    context = {
        "conversation": conversation,
        "user_progress": progress_data,
        "current_video": current_video,
        "current_quiz": current_quiz,
    }

    return render(request, "tutor/conversation.html", context)


@login_required
@require_POST
def send_message(request, conversation_id):
    """HTMX endpoint to handle user messages."""
    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )
    message_text = request.POST.get("message", "").strip()

    if not message_text:
        return HttpResponseBadRequest("Message content is required")

    # Create new message
    message = Message.objects.create(
        conversation=conversation, role="user", content=message_text
    )

    # Update conversation timestamp
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=["updated_at"])

    # Process the message using Celery task - send just the ID and text
    process_user_message.delay(
        conversation_id=conversation.id,
        user_id=request.user.id,
        message=message_text,
    )

    # Return the rendered message template
    return render(request, "tutor/partials/message.html", {"message": message})


@login_required
@require_POST
def generate_quiz(request):
    """HTMX endpoint to generate a quiz."""
    conversation_id = request.POST.get("conversation_id")
    video_id = request.POST.get("video_id")
    difficulty = request.POST.get("difficulty", "beginner")
    question_count = request.POST.get("question_count", "5")

    if not conversation_id or not video_id:
        return HttpResponseBadRequest("Missing required parameters")

    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )

    # Start asynchronous quiz generation
    from .tasks import generate_quiz_task

    generate_quiz_task.delay(
        conversation_id=conversation_id,
        video_id=video_id,
        difficulty=difficulty,
        question_count=question_count,
    )

    # Return a loading indicator
    return render(
        request,
        "tutor/partials/quiz_loading.html",
        {"conversation": conversation, "video": {"video_id": video_id}},
    )


@login_required
@require_POST
def submit_quiz(request):
    """Handle quiz submission and scoring."""
    conversation_id = request.POST.get("conversation_id")

    if not conversation_id:
        return HttpResponseBadRequest("Missing required parameters")

    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )

    # Get quiz data from conversation state
    if not conversation.state.get("current_quiz"):
        return HttpResponseBadRequest("No active quiz found")

    quiz_data = conversation.state["current_quiz"]

    # Process answers
    correct_answers = []
    user_answers = []

    # For each question, check if the answer is correct
    for i, question in enumerate(quiz_data["questions"]):
        correct_answer = question["correct_answer"]
        user_answer = int(request.POST.get(f"answer_{i}", -1))

        correct_answers.append(user_answer == correct_answer)
        user_answers.append(user_answer)

    # Calculate score
    if correct_answers:
        score = sum(correct_answers) / len(correct_answers) * 100
    else:
        score = 0

    # Create quiz attempt record
    quiz_attempt = QuizAttempt.objects.create(
        conversation=conversation,
        user=request.user,
        video_id=conversation.state.get("current_video_id"),
        questions=quiz_data["questions"],
        user_answers=user_answers,
        correct_answers=correct_answers,
        score=score,
        completed_at=timezone.now(),
    )

    # Update conversation state
    conversation.state["quiz_attempt"] = {
        "id": quiz_attempt.id,
        "score": score,
        "correct_count": sum(correct_answers),
        "user_answers": user_answers,
        "completed_at": quiz_attempt.completed_at.isoformat(),
    }
    conversation.save(update_fields=["state"])

    # Update learning progress
    from .tasks import update_learning_progress

    update_learning_progress.delay(request.user.id, conversation.id)

    # Return updated quiz with results
    return render(
        request,
        "tutor/partials/quiz.html",
        {
            "quiz": quiz_data,
            "quiz_attempt": {
                "id": quiz_attempt.id,
                "score": score,
                "correct_count": sum(correct_answers),
                "user_answers": user_answers,
                "completed_at": quiz_attempt.completed_at,
            },
            "conversation": conversation,
            "video": {"video_id": conversation.state.get("current_video_id")},
        },
    )


@login_required
def get_feedback(request, quiz_attempt_id):
    """Generate learning feedback based on quiz performance."""
    quiz_attempt = get_object_or_404(QuizAttempt, id=quiz_attempt_id, user=request.user)

    # Generate feedback
    correct_count = sum(quiz_attempt.correct_answers)
    total_count = len(quiz_attempt.questions)

    if correct_count == 0:
        performance = "needs significant improvement"
    elif correct_count < total_count / 2:
        performance = "needs improvement"
    elif correct_count < total_count:
        performance = "good"
    else:
        performance = "excellent"

    # Identify areas for improvement
    improvement_areas = []
    for _, (correct, question) in enumerate(
        zip(quiz_attempt.correct_answers, quiz_attempt.questions, strict=False)
    ):
        if not correct:
            # Add the question topic to improvement areas
            question_text = question["question"]

            # Simple topic extraction
            if "vocabulary" in question_text.lower() or any(
                word in question_text.lower() for word in ["mean", "definition", "word"]
            ):
                improvement_areas.append("vocabulary")
            elif "grammar" in question_text.lower() or any(
                word in question_text.lower()
                for word in ["structure", "order", "particle"]
            ):
                improvement_areas.append("grammar")
            elif "translate" in question_text.lower():
                improvement_areas.append("translation")
            else:
                improvement_areas.append("general comprehension")

    # Get unique improvement areas
    improvement_areas = list(set(improvement_areas))

    # Return feedback template
    return render(
        request,
        "tutor/partials/feedback.html",
        {
            "quiz_attempt": quiz_attempt,
            "performance": performance,
            "score": quiz_attempt.score,
            "correct_count": correct_count,
            "total_count": total_count,
            "improvement_areas": improvement_areas,
        },
    )


@login_required
def delete_conversation(request, conversation_id):
    """Delete a conversation."""
    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )

    if request.method == "POST":
        conversation.delete()
        return redirect("tutor:conversation_list")

    # Show confirmation page
    return render(
        request, "tutor/delete_conversation.html", {"conversation": conversation}
    )
