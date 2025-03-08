from django.urls import path
from . import views

app_name = "listening"

urlpatterns = [
    path("", views.index, name="index"),
    path("exercise/<int:pk>/", views.exercise, name="exercise"),
    path("check-translation/", views.check_translation, name="check_translation"),
]
