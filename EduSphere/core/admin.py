# core/admin.py

from django.contrib import admin
from .models import (
    University, UniversityAdmin, Department, Faculty, Student,
    Course, Enrollment, Subject, LearningResource,
    Assignment, AssignmentSubmission, Quiz, Question, MCQOption,
    StudentGrade, Attendance
)

# We can customize the admin interface for a better user experience.

@admin.register(University)
class UniversityAdminView(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Registering the UniversityAdmin profile
admin.site.register(UniversityAdmin)

@admin.register(Department)
class DepartmentAdminView(admin.ModelAdmin):
    list_display = ('name', 'university', 'hod')
    list_filter = ('university',)
    search_fields = ('name', 'hod__user__username')

@admin.register(Faculty)
class FacultyAdminView(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'university')
    list_filter = ('university', 'department')
    search_fields = ('user__username', 'employee_id', 'department__name')

@admin.register(Student)
class StudentAdminView(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'university')
    list_filter = ('university',)
    search_fields = ('user__username', 'student_id')

@admin.register(Course)
class CourseAdminView(admin.ModelAdmin):
    list_display = ('title', 'code', 'department')
    list_filter = ('department__university', 'department')
    search_fields = ('title', 'code')

@admin.register(Subject)
class SubjectAdminView(admin.ModelAdmin):
    list_display = ('title', 'code', 'course')
    list_filter = ('course__department__university', 'course')
    search_fields = ('title', 'code')
    filter_horizontal = ('faculty',)  # Better UI for ManyToManyFields

# Use an Inline for a better Question/Option creation experience
class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    extra = 4 # Show 4 empty option slots by default

@admin.register(Question)
class QuestionAdminView(admin.ModelAdmin):
    list_display = ('text', 'quiz', 'question_type', 'marks')
    list_filter = ('quiz__subject',)
    inlines = [MCQOptionInline] # Add the options directly on the question page

@admin.register(Quiz)
class QuizAdminView(admin.ModelAdmin):
    list_display = ('title', 'subject', 'due_date')
    list_filter = ('subject',)

@admin.register(Assignment)
class AssignmentAdminView(admin.ModelAdmin):
    list_display = ('title', 'subject', 'due_date', 'total_marks')
    list_filter = ('subject',)

# Register remaining models with the default admin interface for simplicity
admin.site.register(Enrollment)
admin.site.register(LearningResource)
admin.site.register(AssignmentSubmission)
admin.site.register(StudentGrade)
admin.site.register(Attendance)
# MCQOption is managed via the Question admin, so we don't need to register it separately.