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


def handle_search_videos(tool_call, conversation, channel_layer, youtube_service):
    """Handle the search_youtube_videos tool call."""
    result = None
    try:
        logger.info(f"Searching YouTube with query: {tool_call['input']}")
        result = youtube_service.search_videos(**tool_call["input"])
        logger.info(f"YouTube search returned {len(result) if result else 0} results")

        if result:
            # Store in conversation state
            conversation.state["search_results"] = result
            conversation.save(update_fields=["state"])

            # Format a message with the results to show in the chat
            message_text = (
                "Here are some Toki Pona learning videos that might help:\n\n"
            )
            for i, video in enumerate(result[:5], 1):
                message_text += (
                    f"{i}. **{video.get('title')}** by {video.get('channel')}\n"
                )
                message_text += f"   Duration: {video.get('duration')} | [Watch on YouTube]({video.get('url')})\n\n"

            message_text += "Let me know which video you'd like to explore further."

            # Create and send a message with the search results
            assistant_message = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=message_text,
            )

            # Render and send the message
            message_html = render_to_string(
                "tutor/partials/message.html", {"message": assistant_message}
            )

            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.id}",
                {
                    "type": "chat_message",
                    "html": message_html,
                    "message_id": assistant_message.id,
                },
            )
        else:
            result = {
                "error": "No videos found matching your query. Please try a different search."
            }
    except Exception as e:
        logger.error(f"Error executing search_youtube_videos: {str(e)}", exc_info=True)
        result = {"error": f"Failed to search videos: {str(e)}"}

    return result


def handle_video_content(tool_call, conversation, channel_layer, youtube_service):
    """Handle the get_video_content tool call."""
    result = None
    try:
        result = youtube_service.get_video_content(**tool_call["input"])
        if "error" not in result:
            # Store in conversation state
            conversation.state["current_video_id"] = tool_call["input"]["video_id"]
            conversation.save(update_fields=["state"])

            # Format a message about the video
            video_url = (
                f"https://www.youtube.com/watch?v={tool_call['input']['video_id']}"
            )
            message_text = f"**{result.get('title', '')}**\n\n"
            message_text += f"By: {result.get('channel', '')}\n"
            message_text += f"[Watch on YouTube]({video_url})\n\n"

            # Add transcript excerpt if available
            if result.get("transcript"):
                excerpt = (
                    result["transcript"][:500] + "..."
                    if len(result["transcript"]) > 500
                    else result["transcript"]
                )
                message_text += (
                    f"Here's an excerpt from the transcript:\n\n{excerpt}\n\n"
                )
                message_text += "Would you like me to extract the key Toki Pona vocabulary from this video?"

            # Create and send a message
            assistant_message = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=message_text,
            )

            # Render and send the message
            message_html = render_to_string(
                "tutor/partials/message.html", {"message": assistant_message}
            )

            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.id}",
                {
                    "type": "chat_message",
                    "html": message_html,
                    "message_id": assistant_message.id,
                },
            )
    except Exception as e:
        logger.error(f"Error executing get_video_content: {str(e)}", exc_info=True)
        return {"error": f"Failed to get video content: {str(e)}"}

    return result


def handle_extract_vocabulary(tool_call, conversation, channel_layer, claude_service):
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
                # Store in conversation state
                conversation.state["vocabulary"] = result
                conversation.save(update_fields=["state"])

                # Format a message with the vocabulary
                message_text = "Here are the key Toki Pona words from this video:\n\n"
                for word in result[:10]:  # Limit to 10 words for brevity
                    message_text += (
                        f"**{word.get('word')}**: {word.get('definition')}\n"
                    )
                    if "example" in word and word["example"]:
                        message_text += f"Example: _{word['example']}_\n\n"
                    else:
                        message_text += "\n"

                message_text += "Would you like to test your knowledge with a quiz based on this content?"

                # Create and send a message
                assistant_message = Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content=message_text,
                )

                # Render and send the message
                message_html = render_to_string(
                    "tutor/partials/message.html", {"message": assistant_message}
                )

                async_to_sync(channel_layer.group_send)(
                    f"chat_{conversation.id}",
                    {
                        "type": "chat_message",
                        "html": message_html,
                        "message_id": assistant_message.id,
                    },
                )
            else:
                result = {"error": "Could not extract vocabulary from transcript"}
        else:
            result = {"error": "No transcript text available to extract vocabulary"}
    except Exception as e:
        logger.error(f"Error executing extract_vocabulary: {str(e)}", exc_info=True)
        result = {"error": f"Failed to extract vocabulary: {str(e)}"}

    return result


def handle_generate_quiz(tool_call, conversation, channel_layer, claude_service):
    """Handle the generate_quiz tool call."""
    result = None
    try:
        # Get transcript from video if needed
        transcript = ""
        video_title = ""

        if conversation.state.get("current_video_id"):
            video_id = conversation.state["current_video_id"]
            try:
                video = VideoResource.objects.get(youtube_id=video_id)
                if hasattr(video, "transcript"):
                    transcript = video.transcript.content
                    video_title = video.title
            except VideoResource.DoesNotExist:
                # If not in database, try to fetch it
                youtube_service = YouTubeService()
                video_content = youtube_service.get_video_content(video_id)
                transcript = video_content.get("transcript", "")
                video_title = video_content.get("title", "")

        # Create the quiz
        quiz_data = claude_service.generate_quiz(
            difficulty=tool_call["input"].get("difficulty", "beginner"),
            question_count=int(tool_call["input"].get("question_count", 5)),
            transcript=transcript,
            video_title=video_title,
        )

        # Store in conversation state
        if "error" not in quiz_data:
            conversation.state["current_quiz"] = quiz_data
            conversation.save(update_fields=["state"])

            # Format a message with the quiz
            message_text = f"I've created a **{quiz_data.get('difficulty', 'beginner')}** level quiz based on the Toki Pona content we've been discussing.\n\n"
            message_text += f"**{quiz_data.get('title', 'Toki Pona Quiz')}**\n\n"

            # Add first question as preview
            if quiz_data.get("questions"):
                question = quiz_data["questions"][0]
                message_text += f"Question 1: {question['question']}\n\n"

                for i, option in enumerate(question["options"]):
                    message_text += f"{i + 1}. {option}\n"

                message_text += "\nLet me know your answer, and we can go through this quiz together!"

            # Create and send a message
            assistant_message = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=message_text,
            )

            # Render and send the message
            message_html = render_to_string(
                "tutor/partials/message.html", {"message": assistant_message}
            )

            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.id}",
                {
                    "type": "chat_message",
                    "html": message_html,
                    "message_id": assistant_message.id,
                },
            )

            result = quiz_data
        else:
            result = quiz_data  # Contains the error

    except Exception as e:
        logger.error(f"Error executing generate_quiz: {str(e)}", exc_info=True)
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
        return handle_search_videos(
            tool_call, conversation, channel_layer, youtube_service
        )
    elif tool_name == "get_video_content":
        return handle_video_content(
            tool_call, conversation, channel_layer, youtube_service
        )
    elif tool_name == "extract_vocabulary":
        return handle_extract_vocabulary(
            tool_call, conversation, channel_layer, claude_service
        )
    elif tool_name == "generate_quiz":
        return handle_generate_quiz(
            tool_call, conversation, channel_layer, claude_service
        )

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

        # Get just the relevant conversation history - keeping it simple
        conversation_history = list(
            conversation.messages.order_by("created_at").filter(is_tool_call=False)
        )

        # Generate initial response
        response = claude_service.generate_response(conversation_history, message)

        # Handle tool calls first if any
        if response.get("tool_calls"):
            # Show typing indicator during tool execution
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation_id}",
                {"type": "typing_indicator", "is_typing": True},
            )

            for tool_call in response["tool_calls"]:
                # Send a message that a tool is being called
                tool_status_message = Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content=f"Searching for information on {tool_call['name'].replace('_', ' ')}...",
                )

                # Send the status message
                status_html = render_to_string(
                    "tutor/partials/message.html", {"message": tool_status_message}
                )

                async_to_sync(channel_layer.group_send)(
                    f"chat_{conversation_id}",
                    {
                        "type": "chat_message",
                        "html": status_html,
                        "message_id": tool_status_message.id,
                    },
                )

                # Notify about tool execution status
                async_to_sync(channel_layer.group_send)(
                    f"chat_{conversation_id}",
                    {
                        "type": "tool_execution",
                        "tool_name": tool_call["name"],
                        "status": "started",
                    },
                )

                # Create tool call message in database
                tool_message = Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content="",
                    is_tool_call=True,
                    tool_name=tool_call["name"],
                    tool_input=tool_call["input"],
                )

                # Execute the tool
                result = execute_tool_call(
                    tool_call,
                    conversation,
                    channel_layer,
                    claude_service,
                    youtube_service,
                )

                # Save tool result
                tool_message.tool_output = result
                tool_message.save()

                # Create tool result message
                Message.objects.create(
                    conversation=conversation,
                    role="user",
                    content="",
                    is_tool_call=True,
                    tool_name=tool_call["name"],
                    tool_output=result,
                )

                # Handle result status
                if isinstance(result, dict) and "error" in result:
                    error_message = (
                        f"Error using {tool_call['name']}: {result['error']}"
                    )
                    logger.warning(error_message)

                    # Send error message to the chat
                    error_msg = Message.objects.create(
                        conversation=conversation,
                        role="assistant",
                        content=f"I encountered an error while searching: {result['error']}. Let's try a different approach.",
                    )

                    error_html = render_to_string(
                        "tutor/partials/message.html", {"message": error_msg}
                    )

                    async_to_sync(channel_layer.group_send)(
                        f"chat_{conversation_id}",
                        {
                            "type": "chat_message",
                            "html": error_html,
                            "message_id": error_msg.id,
                        },
                    )

                    # Send error status
                    async_to_sync(channel_layer.group_send)(
                        f"chat_{conversation_id}",
                        {
                            "type": "tool_execution",
                            "tool_name": tool_call["name"],
                            "status": "error",
                            "error": error_message,
                        },
                    )
                else:
                    # Send completed status
                    async_to_sync(channel_layer.group_send)(
                        f"chat_{conversation_id}",
                        {
                            "type": "tool_execution",
                            "tool_name": tool_call["name"],
                            "status": "completed",
                            "data": result,
                        },
                    )

            # Create a final response if needed
            final_response = response.get("response_text", "")
            if not final_response:
                logger.info(
                    "No initial response text, skipping final response generation"
                )
            else:
                # Make the response safe for HTML display
                safe_response = mark_safe(final_response)

                # Create the assistant message
                assistant_message = Message.objects.create(
                    conversation=conversation, role="assistant", content=safe_response
                )

                # Render and send the message
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
        else:
            # If there are no tool calls, just send the response
            if response.get("response_text"):
                # Make the response safe for HTML display
                safe_response = mark_safe(response.get("response_text", ""))

                assistant_message = Message.objects.create(
                    conversation=conversation, role="assistant", content=safe_response
                )

                # Render and send the message
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

        # Turn off typing indicator
        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation_id}", {"type": "typing_indicator", "is_typing": False}
        )

        # Update learning progress
        update_learning_progress.delay(user_id, conversation_id)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)

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


@shared_task
def process_video_transcript(video_id, conversation_id=None):
    """Process video transcript in background."""
    try:
        video = VideoResource.objects.get(youtube_id=video_id)
        transcript = video.transcript

        if conversation_id:
            conversation = Conversation.objects.get(id=conversation_id)
            if (
                "current_video_id" in conversation.state
                and conversation.state["current_video_id"] == video_id
            ):
                conversation.state["transcript"] = transcript.content
                conversation.save(update_fields=["state"])

        logger.info(f"Successfully processed transcript for video {video_id}")

    except Exception as e:
        logger.error(f"Error processing transcript: {str(e)}")


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


@shared_task
def generate_quiz_task(
    conversation_id, video_id=None, difficulty="beginner", question_count=5
):
    """Generate a quiz for a video."""
    try:
        # Get a simplified version that just calls handle_generate_quiz
        conversation = Conversation.objects.get(id=conversation_id)
        channel_layer = get_channel_layer()
        claude_service = ClaudeService()

        tool_call = {
            "name": "generate_quiz",
            "input": {
                "video_id": video_id or conversation.state.get("current_video_id"),
                "difficulty": difficulty,
                "question_count": question_count,
            },
        }

        result = handle_generate_quiz(
            tool_call, conversation, channel_layer, claude_service
        )
        return result

    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        return {"error": f"Failed to generate quiz: {str(e)}"}
