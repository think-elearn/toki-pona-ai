import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from .models import (
    Conversation,
    LearningProgress,
    Message,
    QuizAttempt,
    VideoResource,
)
from .services import ClaudeService, YouTubeService

logger = logging.getLogger(__name__)


def handle_search_videos(tool_call, conversation, youtube_service):
    """Handle the search_youtube_videos tool call."""
    result = None
    try:
        result = youtube_service.search_videos(**tool_call["input"])
        if result:
            conversation.state["search_results"] = result
            conversation.save(update_fields=["state"])
        else:
            result = {
                "error": "No videos found matching your query. Please try a different search."
            }
    except Exception as e:
        logger.error(f"Error executing search_youtube_videos: {str(e)}")
        result = {"error": f"Failed to search videos: {str(e)}"}

    return result


def handle_video_content(tool_call, conversation, channel_layer, youtube_service):
    """Handle the get_video_content tool call."""
    result = None
    try:
        result = youtube_service.get_video_content(**tool_call["input"])
        if "error" not in result:
            conversation.state["current_video_id"] = tool_call["input"]["video_id"]
            conversation.save(update_fields=["state"])
    except Exception as e:
        logger.error(f"Error executing get_video_content: {str(e)}")
        return {"error": f"Failed to get video content: {str(e)}"}

    # Only proceed with video panel if we have valid video data
    if not isinstance(result, dict) or "error" in result:
        return result

    video_data = {
        "video_id": tool_call["input"]["video_id"],
        "title": result.get("title", ""),
        "channel": result.get("channel", ""),
        "duration": result.get("duration", ""),
        "transcript": result.get("transcript", ""),
    }

    video_html = render_to_string(
        "tutor/partials/video_panel.html",
        {"video": video_data, "conversation": conversation},
    )

    async_to_sync(channel_layer.group_send)(
        f"chat_{conversation.id}",
        {
            "type": "video_panel",
            "html": video_html,
            "video_id": tool_call["input"]["video_id"],
        },
    )

    process_video_transcript.delay(
        video_id=tool_call["input"]["video_id"],
        conversation_id=conversation.id,
    )

    return result


def handle_extract_vocabulary(tool_call, conversation, claude_service):
    """Handle the extract_vocabulary tool call."""
    result = None
    try:
        transcript_text = tool_call["input"].get("transcript")
        if not transcript_text and conversation.state.get("current_video_id"):
            try:
                video = VideoResource.objects.get(
                    youtube_id=conversation.state["current_video_id"]
                )
                if hasattr(video, "transcript"):
                    transcript_text = video.transcript.content
            except VideoResource.DoesNotExist:
                return {"error": "Video not found in database"}

        if transcript_text:
            result = claude_service.extract_vocabulary(transcript_text)
            if result:
                conversation.state["vocabulary"] = result
                conversation.save(update_fields=["state"])
            else:
                result = {"error": "Could not extract vocabulary from transcript"}
        else:
            result = {"error": "No transcript text available to extract vocabulary"}
    except Exception as e:
        logger.error(f"Error executing extract_vocabulary: {str(e)}")
        result = {"error": f"Failed to extract vocabulary: {str(e)}"}

    return result


def handle_generate_quiz(tool_call, conversation):
    """Handle the generate_quiz tool call."""
    result = None
    try:
        result = generate_quiz_task(
            conversation_id=conversation.id, **tool_call["input"]
        )
        if not result or "error" in result:
            logger.error(
                f"Quiz generation error: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.error(f"Error executing generate_quiz: {str(e)}")
        result = {"error": f"Failed to generate quiz: {str(e)}"}

    return result


def execute_tool_call(
    tool_call, conversation, channel_layer, claude_service, youtube_service
):
    """Helper function to execute a tool call."""
    logger.info(
        f"Executing tool call: {tool_call['name']} with input: {tool_call['input']}"
    )

    tool_name = tool_call["name"]

    if tool_name == "search_youtube_videos":
        return handle_search_videos(tool_call, conversation, youtube_service)
    elif tool_name == "get_video_content":
        return handle_video_content(
            tool_call, conversation, channel_layer, youtube_service
        )
    elif tool_name == "extract_vocabulary":
        return handle_extract_vocabulary(tool_call, conversation, claude_service)
    elif tool_name == "generate_quiz":
        return handle_generate_quiz(tool_call, conversation)

    # Return None for unhandled tool calls
    return None


@shared_task
def process_user_message(conversation_id, user_id, message):
    """Process a user message and generate AI response with potential tool calls."""
    conversation = Conversation.objects.get(id=conversation_id)
    channel_layer = get_channel_layer()

    try:
        # Send typing indicator to show that the AI is thinking
        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation_id}",
            {"type": "typing_indicator", "is_typing": True},
        )

        claude_service = ClaudeService()
        youtube_service = YouTubeService()
        conversation_history = list(conversation.messages.order_by("created_at"))
        response = claude_service.generate_response(conversation_history, message)

        if response.get("tool_calls"):
            # Show typing indicator during tool execution
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation_id}",
                {"type": "typing_indicator", "is_typing": True},
            )

            for tool_call in response["tool_calls"]:
                tool_message = Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content="",
                    is_tool_call=True,
                    tool_name=tool_call["name"],
                    tool_input=tool_call["input"],
                )
                async_to_sync(channel_layer.group_send)(
                    f"chat_{conversation_id}",
                    {
                        "type": "tool_execution",
                        "tool_name": tool_call["name"],
                        "status": "started",
                    },
                )
                result = execute_tool_call(
                    tool_call,
                    conversation,
                    channel_layer,
                    claude_service,
                    youtube_service,
                )
                tool_message.tool_output = result
                tool_message.save()
                async_to_sync(channel_layer.group_send)(
                    f"chat_{conversation_id}",
                    {
                        "type": "tool_execution",
                        "tool_name": tool_call["name"],
                        "status": "completed",
                        "data": result,
                    },
                )

        final_response = response.get("response_text", "")
        if not final_response and response.get("tool_calls"):
            final_response = claude_service.generate_final_response(
                conversation_history
            )

        # Make the response safe for HTML display
        safe_response = mark_safe(final_response)

        assistant_message = Message.objects.create(
            conversation=conversation, role="assistant", content=safe_response
        )

        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation_id}", {"type": "typing_indicator", "is_typing": False}
        )

        # Then send the assistant's message through the channel layer
        message_html = render_to_string(
            "tutor/partials/message.html", {"message": assistant_message}
        )

        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation_id}",
            {
                "type": "chat_message",
                "html": message_html,
                "message_id": assistant_message.id,
            },
        )
        update_learning_progress.delay(user_id, conversation_id)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

        error_text = f"Sorry, there was an error processing your request: {str(e)}"
        safe_error = mark_safe(error_text)

        error_message = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=safe_error,
        )

        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation_id}", {"type": "typing_indicator", "is_typing": False}
        )

        # Send error message with HTML
        error_html = render_to_string(
            "tutor/partials/message.html", {"message": error_message}
        )

        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation_id}",
            {
                "type": "chat_message",
                "html": error_html,
                "message_id": error_message.id,
            },
        )


def process_transcript_segments(transcript):
    """Helper function to process transcript into segments."""
    segments = []
    import re

    if "WEBVTT" in transcript.content or " --> " in transcript.content:
        lines = transcript.content.strip().split("\n")
        i = 0
        while i < len(lines):
            if not lines[i] or lines[i] == "WEBVTT":
                i += 1
                continue

            if " --> " in lines[i]:
                timestamp = lines[i]
                if i + 1 < len(lines):
                    text = lines[i + 1]
                    start_time = timestamp.split(" --> ")[0].strip()
                    segments.append(
                        {
                            "timestamp": timestamp,
                            "text": text,
                            "start_time": start_time,
                        }
                    )
                    i += 2
                else:
                    i += 1
            else:
                i += 1
    else:
        sentences = re.split(r"(?<=[.!?])\s+", transcript.content)
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                segments.append(
                    {
                        "timestamp": f"{i}",
                        "text": sentence.strip(),
                        "start_time": f"{i}",
                    }
                )

    transcript.segments = segments
    transcript.save(update_fields=["segments"])


@shared_task
def process_video_transcript(video_id, conversation_id=None):
    """Process video transcript in background."""
    try:
        video = VideoResource.objects.get(youtube_id=video_id)
        transcript = video.transcript

        if not transcript.segments:
            process_transcript_segments(transcript)

        if not transcript.vocabulary:
            claude_service = ClaudeService()
            vocabulary = claude_service.extract_vocabulary(transcript.content)
            transcript.vocabulary = vocabulary
            transcript.save(update_fields=["vocabulary"])

        if conversation_id:
            conversation = Conversation.objects.get(id=conversation_id)
            if (
                "current_video_id" in conversation.state
                and conversation.state["current_video_id"] == video_id
            ):
                conversation.state["transcript_segments"] = transcript.segments
                conversation.state["vocabulary"] = transcript.vocabulary
                conversation.save(update_fields=["state"])

        logger.info(f"Successfully processed transcript for video {video_id}")

    except Exception as e:
        logger.error(f"Error processing transcript: {str(e)}")
        raise


@shared_task
def generate_quiz_task(
    conversation_id, video_id=None, difficulty="beginner", question_count=5
):
    """Generate a quiz for a video."""
    try:
        conversation = Conversation.objects.get(id=conversation_id)

        if not video_id and conversation.state.get("current_video_id"):
            video_id = conversation.state["current_video_id"]

        if not video_id:
            return {"error": "No video selected for quiz generation"}

        try:
            video = VideoResource.objects.get(youtube_id=video_id)
            transcript = (
                video.transcript.content if hasattr(video, "transcript") else ""
            )
        except VideoResource.DoesNotExist:
            youtube_service = YouTubeService()
            video_content = youtube_service.get_video_content(video_id)
            transcript = video_content.get("transcript", "")
            video_title = video_content.get("title", "")
        else:
            video_title = video.title

        if not transcript:
            return {"error": "No transcript available for quiz generation"}

        claude_service = ClaudeService()
        quiz_data = claude_service.generate_quiz(
            difficulty=difficulty,
            question_count=int(question_count),
            transcript=transcript,
            video_title=video_title,
        )

        if "error" in quiz_data:
            return quiz_data

        conversation.state["current_quiz"] = quiz_data
        conversation.save(update_fields=["state"])

        quiz_html = render_to_string(
            "tutor/partials/quiz.html",
            {
                "quiz": quiz_data,
                "conversation": conversation,
                "video": {"video_id": video_id},
            },
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation_id}",
            {"type": "video_panel", "html": quiz_html, "video_id": video_id},
        )

        return quiz_data

    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        return {"error": f"Failed to generate quiz: {str(e)}"}


@shared_task
def update_learning_progress(user_id, conversation_id):
    """Update user's learning progress based on conversation activity."""
    try:
        user = User.objects.get(id=user_id)
        conversation = Conversation.objects.get(id=conversation_id)

        progress, created = LearningProgress.objects.get_or_create(user=user)

        if created:
            progress.conversations_count = 1
        else:
            progress.conversations_count += 1

        if conversation.state.get("current_video_id"):
            progress.videos_watched += 1

        if conversation.state.get("current_quiz"):
            quiz_attempts = QuizAttempt.objects.filter(
                conversation=conversation, user=user, completed_at__isnull=False
            ).count()

            if quiz_attempts > 0:
                progress.quizzes_completed += 1

        if conversation.state.get("vocabulary"):
            vocabulary = conversation.state["vocabulary"]
            current_known = set(progress.known_vocabulary)

            for word_item in vocabulary:
                word = word_item.get("word")
                if word and word not in current_known:
                    current_known.add(word)
                    progress.vocabulary_strength[word] = 0.3

            progress.known_vocabulary = list(current_known)

        progress.save()
        logger.info(f"Updated learning progress for user {user_id}")

    except Exception as e:
        logger.error(f"Error updating learning progress: {str(e)}")
