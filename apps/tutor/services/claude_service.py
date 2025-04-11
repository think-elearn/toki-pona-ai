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
        self.system_prompt = """You are an intelligent, helpful Toki Pona language tutor designed to provide an interactive learning experience.

        Important guidance:
        1. BE CONCISE - Don't provide lengthy introductions or explanations unless necessary
        2. USE TOOLS NATURALLY - Call tools when appropriate for the learning experience
        3. INCORPORATE TOOL RESULTS SEAMLESSLY - When using tools, integrate the results naturally

        When users ask about Toki Pona topics, use the search_youtube_videos tool to find relevant educational videos.
        When a user selects a video, use the get_video_content tool to retrieve and analyze the video content.
        After retrieving video content, use the extract_vocabulary tool to identify key Toki Pona words.
        When a user wants to test their knowledge, use the generate_quiz tool to create appropriate questions.
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
                    },
                    "required": [],
                },
            },
        ]

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
            # Format messages manually to avoid duplication
            formatted_messages = []

            # Add user message directly if provided - this is the simplest approach
            if new_message:
                formatted_messages.append({"role": "user", "content": new_message})
            else:
                # Just get the last few messages to avoid duplicates
                unique_messages = {}
                for msg in conversation_history[-5:]:  # Only use last 5 messages
                    if msg.role in ["user", "assistant"] and not msg.is_tool_call:
                        # Use content as key to avoid duplicates
                        unique_messages[msg.content] = {
                            "role": msg.role,
                            "content": msg.content,
                        }

                # Convert to list
                formatted_messages = list(unique_messages.values())

            # Log what we're sending
            logger.info(f"Sending {len(formatted_messages)} messages to Claude")
            if len(formatted_messages) > 0:
                logger.info(f"Last message: {formatted_messages[-1]}")

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
                    # Log successful tool call
                    logger.info(f"Claude called tool: {content_item.name}")

            return result

        except Exception as e:
            logger.error(f"Error generating Claude response: {str(e)}", exc_info=True)
            return {
                "response_text": f"I'm having trouble connecting to my knowledge base. Error: {str(e)}",
                "tool_calls": [],
            }

    def _prepare_messages_for_final_response(
        self, conversation_history: List[Message]
    ) -> List[Dict[str, str]]:
        """
        Extract and format messages for the final response.

        Args:
            conversation_history: List of Message objects

        Returns:
            List of formatted messages for Claude API
        """
        user_messages = []
        assistant_messages = []

        # Get the last few non-tool messages
        for msg in conversation_history[-10:]:  # Last 10 messages
            if not msg.is_tool_call:
                if msg.role == "user":
                    user_messages.append({"role": "user", "content": msg.content})
                elif msg.role == "assistant":
                    assistant_messages.append(
                        {"role": "assistant", "content": msg.content}
                    )

        # Only include the last message from each role to avoid duplication
        formatted_messages = []
        if user_messages:
            formatted_messages.append(user_messages[-1])
        if assistant_messages:
            formatted_messages.append(assistant_messages[-1])

        # Add a final user prompt if no messages
        if not formatted_messages:
            formatted_messages.append(
                {
                    "role": "user",
                    "content": "Please summarize what we've learned about Toki Pona.",
                }
            )

        return formatted_messages

    def _extract_response_text(self, response) -> str:
        """
        Extract text from Claude API response.

        Args:
            response: Response from Claude API

        Returns:
            Extracted text response
        """
        for content_item in response.content:
            if content_item.type == "text":
                return content_item.text

        logger.warning("No text response received from Claude")
        return ""

    def generate_final_response(self, conversation_history: List[Message]) -> str:
        """
        Generate a final response after tool execution.

        Args:
            conversation_history: List of Message objects including tool results

        Returns:
            Final response text
        """
        try:
            # Prepare messages for API call
            formatted_messages = self._prepare_messages_for_final_response(
                conversation_history
            )

            # Call Claude API without tools (for final response)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt,
                messages=formatted_messages,
            )

            # Extract text response
            response_text = self._extract_response_text(response)

            if not response_text:
                return "I'm not sure how to respond to that."

            return response_text

        except Exception as e:
            logger.error(
                f"Error generating final Claude response: {str(e)}", exc_info=True
            )
            return f"I'm having trouble generating a complete response. Error: {str(e)}"

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
               - "correct_answer": The correct answer (as an integer index of the options array)
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
