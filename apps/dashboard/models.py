from django.contrib.auth.models import User
from django.db import models


class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    module = models.CharField(max_length=20)  # 'listening', 'writing', 'signing'
    activity = models.CharField(max_length=50)
    score = models.FloatField()
    completed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now=True)
