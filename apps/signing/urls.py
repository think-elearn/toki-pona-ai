from django.urls import path

from . import views

app_name = "signing"

urlpatterns = [
    path("", views.index, name="index"),
    path("practice/<int:pk>/", views.practice, name="practice"),
    path("analyze-sign/", views.analyze_sign, name="analyze_sign"),
    path("track-hands/", views.track_hands, name="track_hands"),
    path(
        "comparison-visualization/<int:pk>/",
        views.comparison_visualization,
        name="comparison_visualization",
    ),
]
