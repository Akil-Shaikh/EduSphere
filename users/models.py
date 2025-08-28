# users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom User Model for Edusphere.
    Inherits from Django's AbstractUser and adds a role field to differentiate
    between different types of users in the system.
    """
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        HOD = "HOD", "HOD"
        FACULTY = "FACULTY", "Faculty"
        STUDENT = "STUDENT", "Student"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"