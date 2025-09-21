# core/models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# -----------------------------------------------------------------------------
# SECTION 1: CORE ORGANIZATIONAL & USER PROFILE MODELS
# -----------------------------------------------------------------------------

class University(models.Model):
    """Represents a single university in the system."""
    name = models.CharField(max_length=200, unique=True)
    
    def __str__(self):
        return self.name

class UniversityAdmin(models.Model):
    """Profile for a University Administrator."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    university = models.OneToOneField(University, on_delete=models.CASCADE) # An admin for one university

    def __str__(self):
        return f"{self.user.username} (Admin for {self.university.name})"

class Department(models.Model):
    """Represents an academic department within a university."""
    name = models.CharField(max_length=200)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='departments')
    # An HOD is a faculty member. Can be null if no HOD is assigned yet.
    hod = models.OneToOneField('Faculty', on_delete=models.SET_NULL, null=True, blank=True, related_name='led_department')

    class Meta:
        unique_together = ('name', 'university') # Department names must be unique within a university

    def __str__(self):
        return f"{self.name} ({self.university.name})"

class Faculty(models.Model):
    """Profile for a Faculty member."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='faculty_members')
    employee_id = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id})"

class Student(models.Model):
    """Profile for a Student."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    # Courses are linked via the Enrollment model below
    enrolled_courses = models.ManyToManyField('Course', through='Enrollment', related_name='students')

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.student_id})"

# -----------------------------------------------------------------------------
# SECTION 2: ACADEMIC STRUCTURE MODELS
# -----------------------------------------------------------------------------

class Course(models.Model):
    """Represents a program of study, e.g., MScIT 1st Year Sem 2."""
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    # Versioning can be handled by creating a new Course instance for a new syllabus
    # or by adding a version field, e.g., version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.title} ({self.code})"

class Enrollment(models.Model):
    """Intermediate model to manage student enrollment in courses."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrollment_date = models.DateField(auto_now_add=True)
    roll_number = models.CharField(max_length=30)

    class Meta:
        unique_together = ('student', 'course') # A student can enroll in a course only once

    def __str__(self):
        return f"{self.student} enrolled in {self.course}"

class Subject(models.Model):
    """Represents a single subject within a course."""
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    # ManyToManyField allows for co-teaching/collaboration
    faculty = models.ManyToManyField(Faculty, related_name='subjects_taught')

    class Meta:
        unique_together = ('code', 'course') # Subject code unique within a course

    def __str__(self):
        return f"{self.title} ({self.code})"

# -----------------------------------------------------------------------------
# SECTION 3: LEARNING & ASSESSMENT MODELS
# -----------------------------------------------------------------------------

class LearningResource(models.Model):
    """Represents learning material like PDFs, notes, or video links."""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='resources/%Y/%m/%d/', blank=True, null=True) # For PDFs, notes
    link = models.URLField(blank=True, null=True) # For video links

    def __str__(self):
        return self.title

class Assignment(models.Model):
    """Represents an assignment for a subject."""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateTimeField()
    total_marks = models.PositiveIntegerField()

    def __str__(self):
        return f"Assignment: {self.title} for {self.subject.title}"

class AssignmentSubmission(models.Model):
    """Represents a student's submission for an assignment."""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assignment_submissions')
    submitted_file = models.FileField(upload_to='submissions/assignments/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"Submission by {self.student} for {self.assignment.title}"

class Quiz(models.Model):
    """Represents a quiz for a subject."""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)
    due_date = models.DateTimeField()

    def __str__(self):
        return f"Quiz: {self.title} for {self.subject.title}"

class Question(models.Model):
    """A question within a quiz."""
    QUESTION_TYPE_CHOICES = [
        ('MCQ', 'Multiple Choice'),
        ('DESCRIPTIVE', 'Descriptive'),
    ]
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=12, choices=QUESTION_TYPE_CHOICES)
    marks = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.text[:50] + "..."

class MCQOption(models.Model):
    """An option for an MCQ-type question."""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class QuizAttempt(models.Model):
    """Links a student to a quiz they have attempted."""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_attempts')
    score = models.PositiveIntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A student can only attempt a quiz once
        unique_together = ('quiz', 'student')

    def __str__(self):
        return f"{self.student}'s attempt on {self.quiz}"

# core/models.py

class StudentAnswer(models.Model):
    """Stores a student's single answer to a question in a quiz attempt."""
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    mcq_option = models.ForeignKey(MCQOption, on_delete=models.CASCADE, null=True, blank=True)
    descriptive_answer = models.TextField(blank=True, null=True)
    marks_awarded = models.PositiveIntegerField(null=True, blank=True) # New Field

    def __str__(self):
        return f"Answer to Q: {self.question.text[:30]}..."

# -----------------------------------------------------------------------------
# SECTION 4: TRANSCRIPT & PROGRESS MODELS
# -----------------------------------------------------------------------------

class StudentGrade(models.Model):
    """Stores the final grade for a student in a particular subject."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades')
    # Storing both letter grade and points makes GPA calculation easier
    grade = models.CharField(max_length=2) # e.g., 'A+', 'B', 'C-'
    points = models.DecimalField(max_digits=3, decimal_places=2) # e.g., 4.00, 3.33

    class Meta:
        unique_together = ('student', 'subject')
    
    def __str__(self):
        return f"{self.student}: {self.subject.code} - {self.grade}"

class Attendance(models.Model):
    """Tracks student attendance for a subject on a given date."""
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    
    class Meta:
        unique_together = ('student', 'subject', 'date')

    def __str__(self):
        return f"{self.student} - {self.subject.code} on {self.date}: {self.status}"