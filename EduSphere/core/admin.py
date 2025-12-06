

from django.contrib import admin

from .models import (
    University, UniversityAdmin, Department, Faculty, Student,
    Course, Enrollment, Subject, LearningResource,
    Assignment, AssignmentSubmission, Quiz, Question, MCQOption,Notification,StudentAnswer,QuizAttempt
)

@admin.register(University)
class UniversityAdminView(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter=('name',)


@admin.register(Department)
class DepartmentAdminView(admin.ModelAdmin):
    list_display = ('name', 'university', 'hod')
    list_filter = ('university',)
    search_fields = ('name', 'hod__user__username')

@admin.register(Faculty)
class FacultyAdminView(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'university')
    list_filter = ('university', 'department__name',)
    search_fields = ('user__username', 'employee_id', 'department__name')

@admin.register(Student)
class StudentAdminView(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'university')
    list_filter = ('university','student_id')
    search_fields = ('user__username', 'student_id')

@admin.register(Course)
class CourseAdminView(admin.ModelAdmin):
    list_display = ('title', 'code', 'department')
    list_filter = ('department__university', 'department__name')
    search_fields = ('title', 'code')

@admin.register(Subject)
class SubjectAdminView(admin.ModelAdmin):
    list_display = ('title', 'code', 'course')
    list_filter = ('course__department__university', 'course')
    search_fields = ('title', 'code')
    filter_horizontal = ('faculty',)


class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    extra = 4 

@admin.register(Question)
class QuestionAdminView(admin.ModelAdmin):
    list_display = ('text', 'quiz', 'question_type', 'marks')
    list_filter = ('quiz__subject',)
    inlines = [MCQOptionInline] 

@admin.register(Quiz)
class QuizAdminView(admin.ModelAdmin):
    list_display = ('title', 'subject', 'due_date')
    list_filter = ('subject',)

@admin.register(Assignment)
class AssignmentAdminView(admin.ModelAdmin):
    list_display = ('title', 'subject', 'due_date', 'total_marks')
    list_filter = ('subject',)


admin.site.register(UniversityAdmin)
admin.site.register(Enrollment)
admin.site.register(LearningResource)
admin.site.register(AssignmentSubmission)
admin.site.register(Notification)
admin.site.register(StudentAnswer)
admin.site.register(QuizAttempt)

