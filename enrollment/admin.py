# enrollment/admin.py
from django.contrib import admin
from .models import Enrollment

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'program', 'roll_number', 'enrollment_date')
    search_fields = ('student__username', 'program__title', 'roll_number')