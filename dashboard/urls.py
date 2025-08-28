# dashboard/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # This will be the home page for logged-in users
    path('', views.dashboard_view, name='dashboard'),
    path('course/<int:pk>/', views.course_detail_view, name='course_detail'),
    path('content/<int:pk>/', views.content_detail_view, name='content_detail'),
    path('course/<int:pk>/manage/', views.manage_course_view, name='manage_course'),
    path('module/<int:pk>/manage/', views.manage_module_view, name='manage_module'),
    path('content/<int:pk>/edit/', views.edit_content_view, name='edit_content'),
    path('content/<int:pk>/delete/', views.delete_content_view, name='delete_content'),
     path('module/<int:pk>/edit/', views.edit_module_view, name='edit_module'),
    path('module/<int:pk>/delete/', views.delete_module_view, name='delete_module'),
]