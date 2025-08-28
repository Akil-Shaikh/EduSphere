# academics/models.py

from django.db import models
from django.conf import settings
from university.models import Department

class Program(models.Model):
    """
    Represents an academic program, like 'Bachelor of Computer Applications'.
    """
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')

    def __str__(self):
        return f"{self.title} ({self.code})"

class Course(models.Model):
    """
    Represents a specific course or subject, like 'Data Structures'.
    It belongs to a program and is taught in a specific semester by a faculty member.
    """
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='courses')
    semester = models.PositiveIntegerField()
    
    # The instructor for the course must be a user with the 'FACULTY' role.
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses_taught',
        limit_choices_to={'role': 'FACULTY'}
    )

    def __str__(self):
        return f"{self.title} (Sem {self.semester}) - {self.program.code}"

class Module(models.Model):
    """
    A module or chapter within a course, e.g., 'Week 1: Introduction to Arrays'.
    """
    title = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.title}"

class Content(models.Model):
    """
    Represents a piece of learning content within a module.
    It can be text, a file, or a video link.
    """
    class ContentType(models.TextChoices):
        TEXT = "TEXT", "Text"
        FILE = "FILE", "File"
        VIDEO_URL = "VIDEO_URL", "Video URL"

    title = models.CharField(max_length=200)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='contents')
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    
    text_content = models.TextField(blank=True)
    file_content = models.FileField(upload_to='content_files/', blank=True)
    video_url = models.URLField(blank=True)
    
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.title} ({self.get_content_type_display()})"