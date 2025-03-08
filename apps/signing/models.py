from django.db import models


class SignReference(models.Model):
    name = models.CharField(max_length=50)
    video = models.FileField(upload_to="signs/", null=True, blank=True)
    landmarks = models.JSONField(null=True)  # Store MediaPipe landmarks
