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
        self.system_prompt = """You are an intelligent and helpful Toki Pona language assistant. You guide users through learning Toki Pona by providing explanations, suggesting resources, and creating practice exercises.

Key information about Toki Pona:
- Toki Pona is a minimalist constructed language created by linguist Sonja Lang
- It has around 120-130 words and simple grammatical structures
- It's designed to promote simple thinking and a positive attitude

Your role:
- Recommend appropriate YouTube videos for learning specific Toki Pona concepts
- Explain grammar rules and vocabulary in clear, concise terms
- Create quizzes and practice exercises tailored to the user's level
- Provide accurate, helpful feedback on user's translations
- Make learning fun and engaging

When explaining Toki Pona concepts:
- Provide examples to illustrate the point
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
        self, conversation_history: List[Message], include_system_prompt: bool = True
    ) -> List[Dict[str, str]]:
        """
        Format conversation history into the format expected by Claude API.

        Args:
            conversation_history: List of Message objects
            include_system_prompt: Whether to include the system prompt

        Returns:
            List of message dictionaries for Claude API
        """
        formatted_messages = []

        # Add system prompt if specified
        if include_system_prompt:
            formatted_messages.append({"role": "system", "content": self.system_prompt})

        # Format each message in the conversation history
        for message in conversation_history:
            # Handle regular text messages
            if not message.is_tool_call:
                formatted_messages.append(
                    {"role": message.role, "content": message.content}
                )
            # Handle tool calls (sent as JSON in special format)
            else:
                if message.role == "assistant":
                    # Tool call by assistant
                    formatted_messages.append(
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": f"tool_{message.id}",
                                    "name": message.tool_name,
                                    "input": message.tool_input,
                                }
                            ],
                        }
                    )
                elif message.role == "user" and message.tool_output:
                    # Tool result from user
                    formatted_messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": f"tool_{message.id - 1}",  # Assumes tool results directly follow tool calls
                                    "content": json.dumps(message.tool_output),
                                }
                            ],
                        }
                    )

        return formatted_messages

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

            # Format messages for Claude API
            formatted_messages = self._format_messages(messages)

            # Call Claude API with tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
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

            # Call Claude API without tools (for final response)
            response = self.client.messages.create(
                model=self.model, max_tokens=2048, messages=formatted_messages
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
