# academics/admin.py
from django.contrib import admin
from .models import Program, Course, Module, Content

class ContentInline(admin.TabularInline):
    model = Content
    extra = 1  # Number of empty forms to display

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'program', 'semester', 'faculty')
    inlines = [ModuleInline]

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    inlines = [ContentInline]

# Register the other models normally
admin.site.register(Program)
admin.site.register(Content)