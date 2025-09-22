# core/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication Views
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Application Views
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('notifications/', views.NotificationListView.as_view(), name='notification_list'), # New URL
    
     # --- NEW UNIVERSITY ADMIN URLs ---
    path('u-admin/', views.UniversityAdminDashboardView.as_view(), name='uni_admin_dashboard'),
    path('u-admin/departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('u-admin/departments/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('u-admin/departments/<int:pk>/update/', views.DepartmentUpdateView.as_view(), name='department_update'),
    path('u-admin/students/', views.StudentListView.as_view(), name='student_list'),
    path('u-admin/students/register/', views.StudentRegistrationView.as_view(), name='student_register'),
    path('u-admin/faculty/', views.FacultyListView.as_view(), name='faculty_list'),
    path('u-admin/faculty/register/', views.FacultyRegistrationView.as_view(), name='faculty_register'),
    path('u-admin/students/register/', views.StudentRegistrationView.as_view(), name='student_register'),
    path('u-admin/students/bulk-register/', views.StudentBulkRegistrationView.as_view(), name='student_bulk_register'), # New
    
    # Course Management for HOD
    path('courses/', views.HODCourseListView.as_view(), name='hod_course_list'),
    path('courses/create/', views.CourseCreateView.as_view(), name='course_create'),
    path('courses/<int:pk>/update/', views.CourseUpdateView.as_view(), name='course_update'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'), # New
    path('courses/<int:course_pk>/subjects/create/', views.SubjectCreateView.as_view(), name='subject_create'), # New
    path('subjects/<int:pk>/update/', views.SubjectUpdateView.as_view(), name='subject_update'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),
    path('courses/<int:course_pk>/enroll/', views.EnrollStudentView.as_view(), name='enroll_student'), # New
    path('unenroll/<int:pk>/', views.UnenrollStudentView.as_view(), name='unenroll_student'), 
    path('courses/<int:course_pk>/bulk-enroll/', views.StudentBulkEnrollmentView.as_view(), name='student_bulk_enroll'), # New URL
    
    
    path('student/courses/', views.StudentCourseListView.as_view(), name='student_course_list'),
    path('student/courses/<int:pk>/', views.StudentCourseDetailView.as_view(), name='student_course_detail'),
    path('student/assignments/<int:pk>/', views.StudentAssignmentDetailView.as_view(), name='student_assignment_detail'),

    path('faculty/subjects/', views.FacultySubjectListView.as_view(), name='faculty_subject_list'),
    path('faculty/subjects/<int:pk>/', views.FacultySubjectDetailView.as_view(), name='faculty_subject_detail'),
    path('faculty/subjects/<int:subject_pk>/resources/create/', views.ResourceCreateView.as_view(), name='resource_create'),
    path('student/transcript/', views.StudentTranscriptView.as_view(), name='student_transcript'),
    path('student/profile/', views.StudentProfileView.as_view(), name='student_profile'),

    # --- NEW STUDENT QUIZ URLs ---
    path('student/quizzes/<int:pk>/take/', views.TakeQuizView.as_view(), name='take_quiz'),
    path('student/quiz_attempt/<int:pk>/result/', views.QuizResultView.as_view(), name='quiz_result'),
    
    # --- NEW ASSIGNMENT URLs ---
    path('subjects/<int:subject_pk>/assignments/create/', views.AssignmentCreateView.as_view(), name='assignment_create'),
    path('assignments/<int:pk>/update/', views.AssignmentUpdateView.as_view(), name='assignment_update'),
    path('assignments/<int:pk>/delete/', views.AssignmentDeleteView.as_view(), name='assignment_delete'),
    path('assignments/<int:pk>/submissions/', views.SubmissionListView.as_view(), name='view_submissions'),
    path('submissions/<int:pk>/grade/', views.GradeSubmissionView.as_view(), name='grade_submission'),
    # --- NEW QUIZ URLs ---
    path('subjects/<int:subject_pk>/quizzes/create/', views.QuizCreateView.as_view(), name='quiz_create'),
    path('quizzes/<int:pk>/', views.QuizDetailView.as_view(), name='quiz_detail'), # The "Quiz Builder" page
    path('quizzes/<int:pk>/update/', views.QuizUpdateView.as_view(), name='quiz_update'),
    path('quizzes/<int:pk>/delete/', views.QuizDeleteView.as_view(), name='quiz_delete'),
    path('quizzes/<int:quiz_pk>/questions/add/', views.QuestionCreateView.as_view(), name='question_create'),
    path('quizzes/<int:pk>/attempts/', views.QuizAttemptsListView.as_view(), name='quiz_attempts_list'),
    path('quiz_attempt/<int:pk>/grade/', views.GradeQuizAttemptView.as_view(), name='grade_quiz_attempt'),
]
