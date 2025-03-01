from django.db import models
from django.contrib.auth.models import AbstractUser


class ExampleUser(AbstractUser):
    token = models.TextField(unique=True, blank=True, null=True)
    gmail = models.CharField(max_length=255, unique=True, blank=True, null=True)

    class Meta:
        ordering = ["username"]
