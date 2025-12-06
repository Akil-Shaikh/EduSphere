# core/context_processors.py

from .models import Notification, Department

def user_context(request):
    if not request.user.is_authenticated:
        return {}

    
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    user_role = None
    user_university = None
    user_department = None

    faculty_subjects = []
 
    user = request.user
    if user.is_superuser:
        user_role = "Superuser"
    elif hasattr(user, 'universityadmin'):
        user_role = "University Admin"
        user_university = user.universityadmin.university
    elif hasattr(user, 'faculty'):
        user_university = user.faculty.university
        user_department = user.faculty.department
        faculty_subjects = user.faculty.subjects_taught.all().order_by('title')
        if Department.objects.filter(hod=user.faculty).exists():
            user_role = "Head of Department"
        else:
            user_role = "Faculty"
    elif hasattr(user, 'student'):
        user_role = "Student"
        user_university = user.student.university
        departments = Department.objects.filter(courses__students=user.student).distinct()
        user_department = ", ".join([dept.name for dept in departments]) or "Not assigned to any department"

    return {
        'unread_notifications_count': unread_count,
        'user_role': user_role,
        'user_university': user_university,
        'user_department': user_department,
        'faculty_subjects': faculty_subjects,
    }