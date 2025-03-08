from django.db import models


class TokiPonaPhrase(models.Model):
    text = models.CharField(max_length=200)
    translations = models.JSONField()  # Store multiple valid translations
    audio_file = models.FileField(upload_to="audio/", null=True, blank=True)
