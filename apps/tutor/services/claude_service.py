import json
import logging

from anthropic import Anthropic
from django.conf import settings

logger = logging.getLogger(__name__)


class ClaudeService:
    """Ultra-minimal service for interacting with Claude API."""

    def __init__(self):
        """Initialize the Claude service with API credentials."""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL_SONNET
        self.system_prompt = """You are a helpful Toki Pona language tutor. Use tools when appropriate."""

        # Define the tools we'll use
        self.tools = [
            {
                "name": "search_youtube_videos",
                "description": "Searches YouTube for Toki Pona learning videos",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query related to Toki Pona",
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
                "description": "Retrieves video content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "video_id": {
                            "type": "string",
                            "description": "YouTube video ID",
                        }
                    },
                    "required": ["video_id"],
                },
            },
            {
                "name": "extract_vocabulary",
                "description": "Extracts vocabulary from transcript",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "transcript": {
                            "type": "string",
                            "description": "Transcript text",
                        }
                    },
                    "required": ["transcript"],
                },
            },
            {
                "name": "generate_quiz",
                "description": "Creates a quiz",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "difficulty": {
                            "type": "string",
                            "enum": ["beginner", "intermediate", "advanced"],
                            "description": "The difficulty level",
                            "default": "beginner",
                        },
                        "question_count": {
                            "type": "integer",
                            "description": "Number of questions",
                            "default": 5,
                        },
                    },
                    "required": [],
                },
            },
        ]

    def generate_response(self, conversation_history=None, message=None):
        """Generate a response using only the direct message."""
        try:
            # Only use the direct message, ignore conversation history
            if message:
                formatted_messages = [{"role": "user", "content": message}]
            else:
                # Fall back to empty message if none provided
                formatted_messages = [
                    {"role": "user", "content": "Tell me about Toki Pona."}
                ]

            logger.info(
                f"Sending 1 message to Claude: {formatted_messages[0]['content'][:30]}..."
            )

            # Call Claude API
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
                    tool_call = {"name": content_item.name, "input": content_item.input}
                    result["tool_calls"].append(tool_call)
                    logger.info(f"Claude called tool: {content_item.name}")

            return result

        except Exception as e:
            logger.error(f"Error generating Claude response: {str(e)}", exc_info=True)
            return {
                "response_text": f"Error connecting to AI service: {str(e)}",
                "tool_calls": [],
            }

    def generate_final_response(self, history=None):
        """Generate a simple final response."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": "Can you summarize what we've learned about Toki Pona?",
                    }
                ],
            )

            for content_item in response.content:
                if content_item.type == "text":
                    return content_item.text

            return "I'm not sure how to respond."
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return f"Sorry, I encountered an error: {str(e)}"

    def extract_vocabulary(self, transcript):
        """Simplified vocabulary extraction."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system="Extract Toki Pona vocabulary with definitions",
                messages=[
                    {
                        "role": "user",
                        "content": f"Extract vocabulary from this text:\n\n{transcript[:4000]}",
                    }
                ],
            )

            for content_item in response.content:
                if content_item.type == "text":
                    # Try to extract JSON if present
                    try:
                        if "```json" in content_item.text:
                            json_text = content_item.text.split("```json")[1].split(
                                "```"
                            )[0]
                            return json.loads(json_text)
                        else:
                            # Just return some basic words
                            return [
                                {
                                    "word": "toki",
                                    "definition": "hello, language, to talk",
                                },
                                {"word": "pona", "definition": "good, simple, to fix"},
                            ]
                    except json.JSONDecodeError:
                        # Fallback to basic words if parsing fails
                        return [
                            {"word": "toki", "definition": "hello, language, to talk"},
                            {"word": "pona", "definition": "good, simple, to fix"},
                        ]

            return []
        except Exception as e:
            logger.error(f"Error extracting vocabulary: {str(e)}")
            return []

    def generate_quiz(
        self, difficulty="beginner", question_count=5, transcript="", video_title=""
    ):
        """Simplified quiz generation."""
        try:
            # Create a very basic quiz
            return {
                "title": "Toki Pona Quiz",
                "difficulty": difficulty,
                "questions": [
                    {
                        "question": "What does 'toki' mean?",
                        "options": ["hello", "goodbye", "tree", "water"],
                        "correct_answer": 0,
                        "explanation": "'toki' means 'hello', 'language', or 'to talk'",
                    },
                    {
                        "question": "What does 'pona' mean?",
                        "options": ["bad", "good", "strange", "big"],
                        "correct_answer": 1,
                        "explanation": "'pona' means 'good', 'simple', or 'to fix'",
                    },
                ],
            }
        except Exception as e:
            logger.error(f"Error generating quiz: {str(e)}")
            return {"error": str(e)}
