# university/models.py

from django.db import models
from django.conf import settings

class University(models.Model):
    """
    Represents a single university or institution on the platform.
    """
    name = models.CharField(max_length=200, unique=True)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Universities"

    def __str__(self):
        return self.name

class Department(models.Model):
    """
    Represents a department within a university, e.g., 'Computer Science'.
    Each department is linked to a single university and has one HOD.
    """
    name = models.CharField(max_length=200)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='departments')
    
    # The Head of Department (HOD) is a user with the 'HOD' role.
    hod = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_department',
        limit_choices_to={'role': 'HOD'}
    )

    class Meta:
        # Ensures a department name is unique within its university
        unique_together = ('name', 'university')

    def __str__(self):
        return f"{self.name} ({self.university.name})"