# rest_api/urls.py

from django.urls import path
from . import views

app_name = 'rest_api'

urlpatterns = [
    path('students/', views.StudentListAPIView.as_view(), name='student-list'),
    path('students/<int:pk>/', views.StudentDetailAPIView.as_view(), name='student-detail'),
]