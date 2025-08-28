# enrollment/models.py

from django.db import models
from django.conf import settings
from academics.models import Program
from django.utils import timezone

class Enrollment(models.Model):
    """
    Links a student user to the academic program they are enrolled in.
    Contains student-specific academic information.
    """
    # The student must be a user with the 'STUDENT' role.
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollment',
        limit_choices_to={'role': 'STUDENT'}
    )
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name='enrolled_students')
    roll_number = models.CharField(max_length=50, unique=True)
    enrollment_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.student.username} enrolled in {self.program.code}"