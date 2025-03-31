import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string

from .models import Conversation, Message
from .tasks import process_user_message

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection."""
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.conversation_group_name = f"chat_{self.conversation_id}"
        self.user = self.scope["user"]

        # Reject connection if user is not authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        # Check if conversation exists and belongs to user
        conversation_exists = await self.check_conversation_permission()
        if not conversation_exists:
            await self.close()
            return

        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name, self.channel_name
        )

        await self.accept()
        logger.info(
            f"WebSocket connected: conversation {self.conversation_id}, user {self.user.username}"
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave conversation group
        await self.channel_layer.group_discard(
            self.conversation_group_name, self.channel_name
        )
        logger.info(
            f"WebSocket disconnected: conversation {self.conversation_id}, code {close_code}"
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "message")

            if message_type == "message":
                await self.handle_chat_message(data)
            elif message_type == "typing":
                await self.handle_typing_indicator(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error(f"Failed to parse WebSocket message: {text_data}")

    async def handle_chat_message(self, data):
        """Process a chat message from the user."""
        message_text = data.get("message", "").strip()
        if not message_text:
            return

        # Save user message to database
        message = await self.save_user_message(message_text)

        # Send message back to WebSocket group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                "type": "chat_message",
                "message": message_text,
                "username": self.user.username,
                "message_id": message.id,
                "timestamp": message.created_at.isoformat(),
            },
        )

        # Show typing indicator
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {"type": "typing_indicator", "is_typing": True},
        )

        # Process message asynchronously with Celery
        process_user_message.delay(
            conversation_id=self.conversation_id,
            user_id=self.user.id,
            message=message_text,
        )

    async def handle_typing_indicator(self, data):
        """Handle typing indicator updates."""
        is_typing = data.get("is_typing", False)

        # Broadcast typing status to the group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                "type": "typing_indicator",
                "is_typing": is_typing,
                "username": self.user.username,
            },
        )

    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        message_html = await self.render_message_html(
            content=event["message"],
            role="user" if event.get("username") == self.user.username else "assistant",
            message_id=event.get("message_id"),
            timestamp=event.get("timestamp"),
        )

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"type": "message", "html": message_html}))

    async def typing_indicator(self, event):
        """Send typing indicator status to WebSocket."""
        await self.send(
            text_data=json.dumps({"type": "typing", "is_typing": event["is_typing"]})
        )

    async def tool_execution(self, event):
        """Send tool execution status to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "tool",
                    "tool_name": event["tool_name"],
                    "status": event["status"],
                    "data": event.get("data"),
                }
            )
        )

    async def video_panel(self, event):
        """Send video panel HTML to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {"type": "video", "html": event["html"], "video_id": event["video_id"]}
            )
        )

    @database_sync_to_async
    def check_conversation_permission(self):
        """Check if conversation exists and belongs to user."""
        try:
            Conversation.objects.get(id=self.conversation_id, user=self.user)
            return True
        except Conversation.DoesNotExist:
            logger.warning(
                f"User {self.user.id} attempted to access conversation {self.conversation_id} without permission"
            )
            return False

    @database_sync_to_async
    def save_user_message(self, content):
        """Save user message to database."""
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation, role="user", content=content
        )
        return message

    @database_sync_to_async
    def render_message_html(self, content, role, message_id=None, timestamp=None):
        """Render message HTML template."""
        from django.utils import timezone

        # Create a temporary message object for rendering
        message = Message(
            id=message_id,
            role=role,
            content=content,
            created_at=timezone.now(),  # Use current time if timestamp not provided
        )

        # Render the message template
        return render_to_string("tutor/partials/message.html", {"message": message})
