from django.urls import path

from . import views

app_name = "signing"

urlpatterns = [
    path("", views.index, name="index"),
    path("practice/<int:pk>/", views.practice, name="practice"),
    path("analyze-sign/", views.analyze_sign, name="analyze_sign"),
]
