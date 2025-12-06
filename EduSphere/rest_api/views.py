# rest_api/views.py

from rest_framework import generics
from core.models import Student
from .serializers import StudentSerializer
from core.views import UniversityAdminRequiredMixin

class StudentListAPIView(UniversityAdminRequiredMixin,generics.ListAPIView):
    """
    API view to retrieve a list of all students.
    """
    queryset = Student.objects.select_related('user', 'university').all()
    serializer_class = StudentSerializer


class StudentDetailAPIView(UniversityAdminRequiredMixin,generics.RetrieveAPIView):
    """
    API view to retrieve the details of a single student.
    """
    queryset = Student.objects.select_related('user', 'university').all()
    serializer_class = StudentSerializer
