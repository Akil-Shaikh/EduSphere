# rest_api/serializers.py

from rest_framework import serializers
from core.models import Student

class StudentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Student model.
    Includes fields from the related User model for a complete profile.
    """
    # Get fields from the related User model
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    # Display the university's name instead of its ID for better readability
    university = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Student
        # List all the fields you want to include in the JSON output
        fields = [
            'pk', # The student's primary key
            'student_id',
            'username',
            'first_name',
            'last_name',
            'email',
            'university',
        ]