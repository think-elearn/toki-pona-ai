import json
import logging
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from django.conf import settings

from ..models import Message

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for interacting with Claude API."""

    def __init__(self):
        """Initialize the Claude service with API credentials."""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL_SONNET
        self.system_prompt = """You are an intelligent, helpful Toki Pona language tutor designed to provide an interactive learning experience. You help users learn Toki Pona by guiding conversations naturally, using tools when appropriate, and adapting to their skill level.

        Important guidance:
        1. BE CONCISE - Don't provide lengthy introductions or explanations unless necessary
        2. USE TOOLS NATURALLY - Call tools when they would genuinely enhance the learning experience
        3. INCORPORATE TOOL RESULTS SEAMLESSLY - When using tools, integrate the results naturally
        4. AVOID REPETITION - Don't repeat yourself or restate information unnecessarily
        5. FOCUS ON THE USER'S NEEDS - Tailor responses to their specific questions and learning goals

        Your role:
        - Recommend appropriate YouTube videos for learning specific Toki Pona concepts
        - Explain grammar rules and vocabulary in clear, concise terms
        - Create quizzes and practice exercises tailored to the user's level
        - Provide accurate, helpful feedback on user's translations
        - Make learning fun and engaging

        When explaining Toki Pona concepts:
        - Adapt to beginner, intermediate, or advanced levels based on user's questions
        - Provide clear, practical examples that help users understand concepts
        - Compare to English when helpful for understanding
        - Highlight common mistakes and misconceptions

        Always follow the Toki Pona learning workflow, guiding the conversation naturally through topic selection, content exploration, practice, and assessment.
        """

        # Define the tools we'll use
        self.tools = [
            {
                "name": "search_youtube_videos",
                "description": "Searches YouTube for Toki Pona learning videos matching the query. Use this when the student wants to find videos about specific Toki Pona topics or lessons.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query related to Toki Pona, e.g., 'toki pona basics', 'toki pona grammar'",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_video_content",
                "description": "Retrieves the transcript and metadata for a specific YouTube video. Use this when the student has selected a video to learn from.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "video_id": {
                            "type": "string",
                            "description": "YouTube video ID, a unique identifier for the video",
                        }
                    },
                    "required": ["video_id"],
                },
            },
            {
                "name": "extract_vocabulary",
                "description": "Extracts Toki Pona vocabulary from a transcript with definitions. Use this to help students learn vocabulary from a video.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "transcript": {
                            "type": "string",
                            "description": "The transcript text from which to extract Toki Pona vocabulary",
                        }
                    },
                    "required": ["transcript"],
                },
            },
            {
                "name": "generate_quiz",
                "description": "Creates a quiz based on the current video's content. Use this when the student wants to test their knowledge.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "difficulty": {
                            "type": "string",
                            "enum": ["beginner", "intermediate", "advanced"],
                            "description": "The difficulty level of the quiz",
                            "default": "beginner",
                        },
                        "question_count": {
                            "type": "integer",
                            "description": "Number of questions to generate",
                            "default": 5,
                        },
                        "video_id": {
                            "type": "string",
                            "description": "YouTube video ID to generate quiz from",
                        },
                        "transcript": {
                            "type": "string",
                            "description": "Transcript text to use for quiz generation",
                        },
                    },
                    "required": [],
                },
            },
        ]

    def _format_messages(
        self, conversation_history: List[Message]
    ) -> List[Dict[str, str]]:
        """
        Format conversation history into the format expected by Claude API.

        Args:
            conversation_history: List of Message objects

        Returns:
            List of message dictionaries for Claude API
        """
        formatted_messages = []
        tool_call_ids = {}  # Track tool call IDs for correct pairing

        # Format each message in the conversation history
        for i, message in enumerate(conversation_history):
            # Skip messages with invalid roles (Claude only accepts 'user' and 'assistant')
            if message.role not in ["user", "assistant"]:
                logger.warning(f"Skipping message with invalid role: {message.role}")
                continue

            # Handle regular text messages
            if not message.is_tool_call:
                formatted_messages.append(
                    {"role": message.role, "content": message.content}
                )
            # Handle tool calls (sent as JSON in special format)
            else:
                if message.role == "assistant":
                    # Tool call by assistant
                    tool_id = f"tool_{message.id}"
                    tool_call_ids[message.id] = tool_id
                    formatted_messages.append(
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": tool_id,
                                    "name": message.tool_name,
                                    "input": message.tool_input,
                                }
                            ],
                        }
                    )
                elif message.role == "user" and message.tool_output:
                    # Find the corresponding tool call message
                    tool_call_message = None
                    # Look for the tool call this result responds to
                    for j in range(i - 1, -1, -1):
                        prev_msg = conversation_history[j]
                        if (
                            prev_msg.is_tool_call
                            and prev_msg.role == "assistant"
                            and prev_msg.tool_name == message.tool_name
                        ):
                            tool_call_message = prev_msg
                            break

                    if tool_call_message:
                        tool_use_id = tool_call_ids.get(
                            tool_call_message.id, f"tool_{tool_call_message.id}"
                        )
                        formatted_messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_id,
                                        "content": (
                                            json.dumps(message.tool_output)
                                            if isinstance(
                                                message.tool_output, (dict, list)
                                            )
                                            else str(message.tool_output)
                                        ),
                                    }
                                ],
                            }
                        )
                    else:
                        # If we can't find the tool call, log a warning and skip this message
                        logger.warning(
                            f"Could not find matching tool call for result with ID {message.id}"
                        )
                        continue

        # Log the message count to help with debugging
        logger.info(f"Formatted {len(formatted_messages)} messages for Claude API")
        return formatted_messages

    def _collect_tool_ids(
        self, formatted_messages: List[Dict[str, Any]]
    ) -> tuple[dict, dict]:
        """
        Collect tool_use and tool_result IDs from messages.

        Args:
            formatted_messages: List of formatted message dictionaries

        Returns:
            A tuple of (tool_use_ids, tool_result_refs) dictionaries
        """
        tool_use_ids = {}  # Maps index to ID
        tool_result_refs = {}  # Maps index to tool_use ID it refers to

        for i, msg in enumerate(formatted_messages):
            if msg["role"] == "assistant" and isinstance(msg.get("content"), list):
                for content_item in msg["content"]:
                    if content_item.get("type") == "tool_use":
                        tool_use_ids[i] = content_item.get("id")

            elif msg["role"] == "user" and isinstance(msg.get("content"), list):
                for content_item in msg["content"]:
                    if content_item.get("type") == "tool_result":
                        tool_result_refs[i] = content_item.get("tool_use_id")

        return tool_use_ids, tool_result_refs

    def _identify_skip_indices(
        self, tool_use_ids: dict, tool_result_refs: dict, total_messages: int
    ) -> set:
        """
        Identify which message indices should be skipped.

        Args:
            tool_use_ids: Dictionary mapping message index to tool_use ID
            tool_result_refs: Dictionary mapping message index to referenced tool_use ID
            total_messages: Total number of messages

        Returns:
            Set of indices to skip
        """
        skip_indices = set()

        # Check for tool_use messages without matching tool_result
        for i, msg_id in tool_use_ids.items():
            if msg_id not in tool_result_refs.values():
                # This tool_use has no matching tool_result - skip it
                logger.warning(
                    f"Skipping tool_use at index {i} with ID {msg_id} - no matching tool_result"
                )
                skip_indices.add(i)
            elif i == total_messages - 1:
                # Tool call at the end with no chance for a result - skip it
                logger.warning(
                    f"Skipping final tool_use at index {i} with ID {msg_id} - no room for tool_result"
                )
                skip_indices.add(i)

        return skip_indices

    def _sanitize_formatted_messages(
        self, formatted_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Ensures that tool_use and tool_result messages are properly paired.
        The Claude API requires that every tool_use message must be followed by a tool_result message.

        Args:
            formatted_messages: List of formatted message dictionaries

        Returns:
            A sanitized list of message dictionaries with proper tool_use/tool_result pairing
        """
        if not formatted_messages:
            return []

        # Collect tool IDs from messages
        tool_use_ids, tool_result_refs = self._collect_tool_ids(formatted_messages)

        # Identify indices to skip
        skip_indices = self._identify_skip_indices(
            tool_use_ids, tool_result_refs, len(formatted_messages)
        )

        # Build the sanitized list
        sanitized_messages = [
            msg for i, msg in enumerate(formatted_messages) if i not in skip_indices
        ]

        logger.info(
            f"Sanitized messages from {len(formatted_messages)} to {len(sanitized_messages)}"
        )
        return sanitized_messages

    def generate_response(
        self, conversation_history: List[Message], new_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from Claude with potential tool calls.

        Args:
            conversation_history: List of Message objects
            new_message: Optional new user message to append

        Returns:
            Dict containing response text and/or tool calls
        """
        try:
            # Create a copy of conversation history to avoid modifying the original
            messages = conversation_history.copy()

            # If a new message is provided, add it to the history
            if new_message:
                messages.append(Message(role="user", content=new_message))

            # For simplicity, when there's a new message, only use the last few messages
            # This helps avoid issues with unpaired tool calls from previous conversations
            if new_message and len(messages) > 5:
                # Keep only the most recent messages
                messages = messages[-5:]
                logger.info(f"Trimmed conversation history to {len(messages)} messages")

            # Format messages for Claude API - first try with all messages
            formatted_messages = self._format_messages(messages)

            # Ensure tool_use and tool_result are properly paired
            formatted_messages = self._sanitize_formatted_messages(formatted_messages)

            # Call Claude API with tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt,
                messages=formatted_messages,
                tools=self.tools,
            )

            # Process the response
            result = {"response_text": "", "tool_calls": []}

            for content_item in response.content:
                if content_item.type == "text":
                    result["response_text"] = content_item.text
                elif content_item.type == "tool_use":
                    # Handle tool use
                    tool_call = {"name": content_item.name, "input": content_item.input}
                    result["tool_calls"].append(tool_call)

            return result

        except Exception as e:
            logger.error(f"Error generating Claude response: {str(e)}")
            return {
                "response_text": f"I'm having trouble connecting to my knowledge base. Error: {str(e)}",
                "tool_calls": [],
            }

    def generate_final_response(self, conversation_history: List[Message]) -> str:
        """
        Generate a final response after tool execution.

        Args:
            conversation_history: List of Message objects including tool results

        Returns:
            Final response text
        """
        try:
            # Format messages for Claude API
            formatted_messages = self._format_messages(conversation_history)

            # Log the message count being sent for debugging
            logger.info(
                f"Generating final response with {len(formatted_messages)} messages"
            )

            # Call Claude API without tools (for final response)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt,
                messages=formatted_messages,
            )

            # Extract text response
            for content_item in response.content:
                if content_item.type == "text":
                    return content_item.text

            return "I'm not sure how to respond to that."

        except Exception as e:
            logger.error(f"Error generating final Claude response: {str(e)}")
            return (
                f"I'm having trouble connecting to my knowledge base. Error: {str(e)}"
            )

    def extract_vocabulary(self, transcript: str) -> List[Dict[str, str]]:
        """
        Extract Toki Pona vocabulary from a transcript.

        Args:
            transcript: Transcript text

        Returns:
            List of vocabulary dictionaries with word, definition, and example
        """
        try:
            # Use Claude to extract vocabulary
            system_prompt = """
            You are a Toki Pona language expert. Extract all Toki Pona words from the given transcript.
            For each word:
            1. Provide the Toki Pona word
            2. Provide its English definition
            3. Include an example sentence from the transcript if available

            Format the response as a JSON array of objects with keys: "word", "definition", "example"
            """

            # If transcript is too long, truncate it
            if len(transcript) > 8000:
                transcript = transcript[:8000] + "..."

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Extract Toki Pona vocabulary from this transcript:\n\n{transcript}",
                    }
                ],
            )

            # Extract the text response
            response_text = None
            for content_item in response.content:
                if content_item.type == "text":
                    response_text = content_item.text

            if not response_text:
                return []

            # Try to parse JSON from the response
            try:
                # Find JSON in the response - it may be wrapped in markdown code blocks
                if "```json" in response_text:
                    json_part = (
                        response_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in response_text:
                    json_part = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_part = response_text

                vocabulary = json.loads(json_part)
                return vocabulary
            except json.JSONDecodeError:
                logger.error("Failed to parse vocabulary as JSON")
                return []

        except Exception as e:
            logger.error(f"Error extracting vocabulary: {str(e)}")
            return []

    def generate_quiz(
        self, difficulty="beginner", question_count=5, transcript="", video_title=""
    ) -> Dict[str, Any]:
        """
        Generate a quiz based on video content.

        Args:
            difficulty: Difficulty level of the quiz
            question_count: Number of questions to generate
            transcript: Transcript text
            video_title: Title of the video

        Returns:
            Quiz data dictionary
        """
        try:
            system_prompt = f"""
            You are a Toki Pona language teacher. Create a {difficulty} level quiz with {question_count} questions
            based on the provided transcript from the video "{video_title}".

            For beginner quizzes, focus on:
            - Simple vocabulary recognition
            - Basic sentence structure
            - Matching Toki Pona words to English meanings

            For intermediate quizzes, include:
            - Sentence translation (both directions)
            - Fill-in-the-blank exercises
            - Understanding context

            For advanced quizzes, include:
            - Complex sentence translation
            - Idioms and expressions
            - Creating original Toki Pona sentences

            Format the response as a JSON object with:
            1. "title": Quiz title
            2. "difficulty": The difficulty level
            3. "questions": Array of question objects, each with:
               - "question": The question text
               - "options": Array of possible answers (for multiple choice)
               - "correct_answer": The correct answer
               - "explanation": Brief explanation of the answer

            Use the transcript content to create relevant questions.
            """

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Generate a {difficulty} level Toki Pona quiz based on this transcript:\n\n{transcript}",
                    }
                ],
            )

            # Extract the text response
            response_text = None
            for content_item in response.content:
                if content_item.type == "text":
                    response_text = content_item.text

            if not response_text:
                return {"error": "Failed to generate quiz"}

            # Try to parse JSON from the response
            try:
                # Find JSON in the response - it may be wrapped in markdown code blocks
                if "```json" in response_text:
                    json_part = (
                        response_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in response_text:
                    json_part = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_part = response_text

                quiz = json.loads(json_part)
                return quiz
            except json.JSONDecodeError:
                logger.error("Failed to parse quiz as JSON")
                return {"error": "Failed to parse quiz as JSON"}

        except Exception as e:
            logger.error(f"Error generating quiz: {str(e)}")
            return {"error": str(e)}
