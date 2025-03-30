# Chatbot Implementation Plan

## Overview

This document outlines the implementation plan for transforming the existing Django-based Toki Pona learning application into an AI-powered, chat-first learning experience with embedded YouTube content.

## 1. Real-Time Communication Infrastructure

### Core Components

- **Django Channels**: For WebSocket support and ASGI compatibility
- **WebSockets**: To enable real-time bidirectional communication
- **Celery**: For handling asynchronous tasks and processing jobs
- **Redis**: As message broker for Celery and for caching/session state

### Implementation Details

- Set up Django Channels with proper routing configuration
- Implement WebSocket consumers for chat functionality
- Configure Celery for background processing:
  - YouTube API interactions
  - Transcript processing and embedding generation
  - Quiz creation and assessment
- Use Redis for both Celery broker and result backend

## 2. Deployment & Infrastructure Considerations

### Docker Configuration

- Update `Dockerfile.dev` and `Dockerfile.prod` to include:
  - Channels dependencies
  - ASGI server (Daphne or Uvicorn)
  - Celery worker setup
- Modify `compose.dev.yaml` to include:
  - WebSocket routing
  - Redis container
  - Celery worker and beat containers

### Fly.io Deployment

- Update `fly.toml` for ASGI deployment
- Configure for WebSocket protocol support
- Set up proper scaling with persistent connections
- Ensure Redis instance is properly configured in production
- Implement health checks appropriate for ASGI applications

## 3. Data Model Design

### Entity Relationship Diagram

```text
+-----------------+       +---------------+       +-----------------+
| User            |<------|Conversation   |------>|VideoResource    |
| (Django Auth)   |       |               |       |                 |
+-----------------+       +---------------+       +-----------------+
        |                    |       |                   |
        |                    |       |                   |
        v                    v       v                   v
+-----------------+   +----------+ +-----------+  +--------------+
|LearningProgress |   |Message   | |QuizAttempt|  |Transcript    |
|                 |   |          | |           |  |              |
+-----------------+   +----------+ +-----------+  +--------------+
```

### Core Models

#### Conversation

```python
class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    learning_focus = models.CharField(max_length=50, null=True, blank=True)
    # Metadata about conversation state
    state = models.JSONField(default=dict, blank=True)
```

#### Message

```python
class Message(models.Model):
    class MessageRole(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=MessageRole.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # For tool use tracking
    is_tool_call = models.BooleanField(default=False)
    tool_name = models.CharField(max_length=50, null=True, blank=True)
    tool_input = models.JSONField(null=True, blank=True)
    tool_output = models.JSONField(null=True, blank=True)
```

#### VideoResource

```python
class VideoResource(models.Model):
    youtube_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    channel = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration = models.CharField(max_length=20)  # Format: MM:SS
    thumbnail_url = models.URLField()
    published_at = models.DateTimeField()
    view_count = models.IntegerField(default=0)

    # Categorization
    difficulty = models.CharField(max_length=20,
                                 choices=[("beginner", "Beginner"),
                                          ("intermediate", "Intermediate"),
                                          ("advanced", "Advanced")])
    topics = models.JSONField(default=list, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### Transcript

```python
class Transcript(models.Model):
    video = models.OneToOneField(VideoResource, on_delete=models.CASCADE, related_name="transcript")
    content = models.TextField()
    language = models.CharField(max_length=10, default="en")
    is_generated = models.BooleanField(default=False)
    has_embeddings = models.BooleanField(default=False)
    embeddings = models.BinaryField(null=True, blank=True)  # For storing vector embeddings

    # Store processed segments for easy retrieval
    segments = models.JSONField(default=list)
    vocabulary = models.JSONField(default=list)  # Extracted Toki Pona vocabulary
```

#### LearningProgress

```python
class LearningProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Overall stats
    videos_watched = models.PositiveIntegerField(default=0)
    quizzes_completed = models.PositiveIntegerField(default=0)
    conversations_count = models.PositiveIntegerField(default=0)

    # Vocabulary progress
    known_vocabulary = models.JSONField(default=list)
    vocabulary_strength = models.JSONField(default=dict)  # Word -> strength mapping

    # Skill levels
    listening_level = models.FloatField(default=0.0)  # 0-10 scale
    translation_level = models.FloatField(default=0.0)
    grammar_level = models.FloatField(default=0.0)

    # Learning profile
    interests = models.JSONField(default=list)
    learning_style = models.CharField(max_length=50, null=True, blank=True)

    last_activity = models.DateTimeField(auto_now=True)
```

#### QuizAttempt

```python
class QuizAttempt(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(VideoResource, null=True, blank=True, on_delete=models.SET_NULL)

    # Quiz content
    questions = models.JSONField()
    user_answers = models.JSONField()
    correct_answers = models.JSONField()

    # Results
    score = models.FloatField()  # Percentage correct
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Feedback
    feedback = models.TextField(blank=True)
    areas_for_improvement = models.JSONField(default=list)
```

## 4. Frontend Architecture

### Technology Stack

- **Django Templates**: Base rendering system
- **HTMX**: For AJAX requests, WebSocket interactions, and dynamic content updates
- **AlpineJS**: For reactive components and state management
- **Tailwind CSS**: For styling (if already in use)

### Key Components

- **Chat Interface**:
  - Message stream with user and assistant messages
  - Message typing indicator
  - Contextual suggestions
  - Tool use visibility

- **Content Panel**:
  - YouTube video embedding
  - Transcript display with synchronized highlighting
  - Quiz rendering and interaction
  - Progress visualization

### Template Structure

```text
templates/
├── listening/
│   ├── base_chat.html        # Base template with chat layout
│   ├── index.html            # Entry point/dashboard
│   ├── conversation.html     # Main chat interface
│   ├── partials/             # HTMX-ready partial templates
│   │   ├── message.html      # Individual message rendering
│   │   ├── video_panel.html  # Video embed with controls
│   │   ├── transcript.html   # Transcript display
│   │   ├── quiz.html         # Quiz rendering
│   │   └── feedback.html     # Learning feedback
│   └── components/           # Reusable UI components
│       ├── chat_input.html   # Message input area
│       ├── video_card.html   # Video selection card
│       └── progress_bar.html # Learning progress visualization
```

## 5. Caching Strategy with Redis

### Cache Layers

- **API Response Cache**: Store responses from external APIs (YouTube, Claude)
- **Session State Cache**: Maintain conversation state and context
- **Transcript Cache**: Store processed transcripts for quick retrieval
- **Embedding Cache**: Cache vector embeddings for fast similarity search
- **Quiz Cache**: Store generated quizzes temporarily

### Implementation

```python
# Redis cache configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Celery configuration with Redis
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://redis:6379/1")
```

## 6. Agent Functionality & Learning Flow

### Tools Implementation

#### YouTube Search Tool

```python
def search_youtube_videos(query, limit=5):
    """Search YouTube for Toki Pona videos matching the query."""
    # Implementation using YouTube Data API
    # Return structured video data
```

#### Transcript Processing Tool

```python
def process_video_transcript(video_id):
    """Extract and process the transcript from a YouTube video."""
    # Fetch transcript
    # Process into segments
    # Extract vocabulary
    # Generate embeddings
    # Store in database
```

#### Quiz Generation Tool

```python
def generate_quiz(video_id, difficulty, question_count=5):
    """Generate a quiz based on video content."""
    # Fetch video and transcript
    # Use Claude to generate appropriate questions
    # Structure into quiz format
    # Cache and return quiz data
```

### Learning Flow Sequence

1. **Onboarding**:
   - Initial conversation to understand user's goals and current level
   - Creation of learning profile

2. **Topic Selection**:
   - User expresses interest in specific topic
   - AI suggests relevant videos or concepts

3. **Content Exploration**:
   - AI embeds video and explains key concepts
   - Highlights important segments in transcript

4. **Active Practice**:
   - AI generates relevant quizzes
   - Provides contextual examples and explanations

5. **Progress Assessment**:
   - Tracks user's performance across activities
   - Suggests areas for improvement

6. **Personalized Recommendations**:
   - Recommends next steps based on progress
   - Adapts difficulty and topics based on user performance

## 7. WebSocket & Channels Implementation

### ASGI Configuration

```python
# project/asgi.py
import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

from apps.listening import routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
```

### WebSocket Consumer

```python
# apps/listening/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .tasks import process_user_message
from .models import Conversation, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'

        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave conversation group
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        user = self.scope['user']

        # Save user message
        conversation = Conversation.objects.get(id=self.conversation_id)
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=message
        )

        # Send acknowledgment
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'chat_message',
                'role': 'user',
                'message': message
            }
        )

        # Start processing in Celery
        process_user_message.delay(
            conversation_id=self.conversation_id,
            user_id=user.id,
            message=message
        )

        # Send "typing" indicator
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_indicator',
                'is_typing': True
            }
        )

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'role': event['role'],
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        # Send typing indicator to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': event['is_typing']
        }))

    async def tool_execution(self, event):
        # Send tool execution status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'tool',
            'tool_name': event['tool_name'],
            'status': event['status'],
            'data': event.get('data')
        }))
```

## 8. Celery Tasks

### Task Configuration

```python
# apps/listening/tasks.py
from celery import shared_task
from django.contrib.auth.models import User
from .models import Conversation, Message
from .services import (
    ClaudeService, YouTubeService, TranscriptService, QuizService
)
import asyncio
import json
import channels.layers
from asgiref.sync import async_to_sync

@shared_task
def process_user_message(conversation_id, user_id, message):
    """Process a user message and generate AI response."""
    conversation = Conversation.objects.get(id=conversation_id)
    user = User.objects.get(id=user_id)

    # Initialize services
    claude_service = ClaudeService()
    youtube_service = YouTubeService()

    # Get conversation history
    conversation_history = list(conversation.messages.order_by('created_at'))

    # Get AI response with potential tool calls
    response = claude_service.generate_response(conversation_history, message)

    # Check for tool calls
    if response.get('tool_calls'):
        for tool_call in response['tool_calls']:
            # Create tool call message
            tool_message = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content="",
                is_tool_call=True,
                tool_name=tool_call['name'],
                tool_input=tool_call['input']
            )

            # Notify about tool execution
            channel_layer = channels.layers.get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{conversation_id}',
                {
                    'type': 'tool_execution',
                    'tool_name': tool_call['name'],
                    'status': 'started'
                }
            )

            # Execute appropriate tool
            if tool_call['name'] == 'search_youtube_videos':
                result = youtube_service.search_videos(**tool_call['input'])
            elif tool_call['name'] == 'get_video_content':
                result = youtube_service.get_video_content(**tool_call['input'])
                # Queue transcript processing in separate task
                process_video_transcript.delay(tool_call['input']['video_id'])
            elif tool_call['name'] == 'generate_quiz':
                result = generate_quiz_task(**tool_call['input'])

            # Update tool message with result
            tool_message.tool_output = result
            tool_message.save()

            # Notify about tool completion
            async_to_sync(channel_layer.group_send)(
                f'chat_{conversation_id}',
                {
                    'type': 'tool_execution',
                    'tool_name': tool_call['name'],
                    'status': 'completed',
                    'data': result
                }
            )

    # Process final response based on tool outputs if any
    final_response = claude_service.generate_final_response(conversation_history)

    # Save assistant message
    Message.objects.create(
        conversation=conversation,
        role="assistant",
        content=final_response
    )

    # Send response to WebSocket
    channel_layer = channels.layers.get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{conversation_id}',
        {
            'type': 'chat_message',
            'role': 'assistant',
            'message': final_response
        }
    )

    # Update conversation state
    update_learning_progress.delay(user_id, conversation_id)

@shared_task
def process_video_transcript(video_id):
    """Process video transcript in background."""
    transcript_service = TranscriptService()
    transcript_service.process_transcript(video_id)

@shared_task
def generate_quiz_task(video_id, difficulty='beginner', question_count=5):
    """Generate a quiz for a video."""
    quiz_service = QuizService()
    return quiz_service.create_quiz(video_id, difficulty, question_count)

@shared_task
def update_learning_progress(user_id, conversation_id):
    """Update user's learning progress based on conversation."""
    # Implementation to analyze conversation and update progress metrics
```

## 9. API Services

### Claude Service

```python
class ClaudeService:
    """Service for interacting with Claude API."""

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def generate_response(self, conversation_history, user_message):
        """Generate a response from Claude with potential tool calls."""
        # Implementation using Anthropic API with tools

    def generate_final_response(self, conversation_history):
        """Generate a final response after tool execution."""
        # Implementation using conversation with tool results
```

### YouTube Service

```python
class YouTubeService:
    """Service for interacting with YouTube API."""

    def search_videos(self, query, limit=5):
        """Search YouTube for Toki Pona videos matching the query."""
        # Implementation using YouTube Data API

    def get_video_content(self, video_id):
        """Get detailed information about a specific video."""
        # Implementation to get video metadata and transcript
```

### Transcript Service

```python
class TranscriptService:
    """Service for processing video transcripts."""

    def process_transcript(self, video_id):
        """Process a video transcript for learning purposes."""
        # Implementation to extract and process transcript
        # Generate embeddings and store in database

    def extract_vocabulary(self, transcript):
        """Extract Toki Pona vocabulary from transcript."""
        # Implementation using NLP techniques
```

### Quiz Service

```python
class QuizService:
    """Service for creating and managing quizzes."""

    def create_quiz(self, video_id, difficulty, question_count):
        """Create a quiz based on video content."""
        # Implementation to generate quiz questions

    def evaluate_answers(self, quiz_id, user_answers):
        """Evaluate user's quiz answers."""
        # Implementation to score and provide feedback
```

## 10. Deployment Updates

### ASGI Configuration for Fly.io

Update `fly.toml`:

```toml
[build]
  dockerfile = 'Dockerfile.prod'

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ['app']

[services.concurrency]
  type = "connections"
  hard_limit = 1000
  soft_limit = 500

[[statics]]
  guest_path = '/app/staticfiles'
  url_prefix = '/static'

[deploy]
  release_command = "python manage.py migrate --noinput"

[processes]
  app = "daphne -b 0.0.0.0 -p 8000 project.asgi:application"
  worker = "celery -A project worker --loglevel=info"
  beat = "celery -A project beat --loglevel=info"
```

### Updated Dockerfile.prod

```dockerfile
# ... [existing content] ...

# Install additional dependencies for Channels and Celery
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    git \
    # ... [existing dependencies] ...
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ... [existing content] ...

# Update ASGI configuration
ENV DJANGO_SETTINGS_MODULE=config.settings.production
# Command will be specified in fly.toml processes
```

## 11. Timeline and Milestones

### Phase 1: Foundation (Week 1-2)

- Set up Django Channels and WebSocket infrastructure
- Implement basic chat interface with WebSocket support
- Create initial data models
- Configure Celery with Redis

### Phase 2: Core Functionality (Week 3-4)

- Implement YouTube service integration
- Develop transcript processing capabilities
- Create basic Claude integration for chat
- Build embedded video panel

### Phase 3: Learning Features (Week 5-6)

- Implement quiz generation and assessment
- Develop progress tracking system
- Create vocabulary extraction and learning system
- Build recommendation functionality

### Phase 4: Polish and Deployment (Week 7-8)

- Optimize response times and caching
- Refine UI/UX for learning flow
- Comprehensive testing of all features
- Deploy to Fly.io with all required services

## 12. Conclusion

This implementation plan provides a comprehensive roadmap for transforming the existing Toki Pona learning application into an AI-powered, chat-first learning platform. By leveraging Django Channels, Celery, and Redis alongside the Anthropic Claude API and YouTube services, we can create an engaging, interactive learning experience that guides users through their Toki Pona language journey.

The modular approach allows for incremental development and testing, while the WebSocket-based communication enables the real-time, dynamic interactions necessary for an effective conversational learning platform.

## Postscript: pgvector Implementation

**Database Setup:**

- Add pgvector extension to PostgreSQL
- Create vector columns for storing embeddings
- Set up appropriate indexes for similarity searches

**Model Updates:**

- Modify the Transcript model to use pgvector's VectorField instead of BinaryField
- Add similarity search methods to relevant models

**Configuration:**

- Update Django settings to include pgvector support
- Configure connection parameters for vector operations

**Search Implementation:**

- Create functions for semantic search across transcripts
- Implement relevance ranking based on vector similarity
