from django.urls import path
from . import views

app_name = "writing"

urlpatterns = [
    path("", views.index, name="index"),
    path("practice/<str:glyph_name>/", views.practice, name="practice"),
    path("check-drawing/", views.check_drawing, name="check_drawing"),
]
