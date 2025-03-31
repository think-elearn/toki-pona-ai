from django.urls import path

from . import views

app_name = "tutor"

urlpatterns = [
    # Original phrase-based practice views
    path("", views.index, name="index"),
    path("exercise/<int:pk>/", views.exercise, name="exercise"),
    path("check-translation/", views.check_translation, name="check_translation"),
    # Conversation-based chat interface
    path("conversations/", views.conversation_list, name="conversation_list"),
    path(
        "conversations/create/", views.create_conversation, name="create_conversation"
    ),
    path(
        "conversations/<int:conversation_id>/",
        views.conversation_view,
        name="conversation",
    ),
    path(
        "conversations/<int:conversation_id>/delete/",
        views.delete_conversation,
        name="delete_conversation",
    ),
    path(
        "conversations/<int:conversation_id>/send/",
        views.send_message,
        name="send_message",
    ),
    # Quiz and learning functionality
    path("generate-quiz/", views.generate_quiz, name="generate_quiz"),
    path("submit-quiz/", views.submit_quiz, name="submit_quiz"),
    path("feedback/<int:quiz_attempt_id>/", views.get_feedback, name="get_feedback"),
]
