# core/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import AssignmentSubmission,Question,MCQOption,Quiz,Assignment , Department, Faculty,Subject
from django.contrib.auth.models import User
class StudentRegistrationForm(forms.ModelForm):
    student_id = forms.CharField(max_length=20, help_text="The unique ID for the student.")
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {'password': forms.PasswordInput()}
        help_texts = {'username': None}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

    # --- NEW VALIDATION METHODS ---
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email


class FacultyRegistrationForm(forms.ModelForm):
    employee_id = forms.CharField(max_length=20)
    department = forms.ModelChoiceField(queryset=Department.objects.none())

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {'password': forms.PasswordInput()}
        help_texts = {'username': None}

    def __init__(self, *args, **kwargs):
        university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)
        if university:
            self.fields['department'].queryset = Department.objects.filter(university=university)
        for field in self.fields.values():
            field.required = True
            
    # --- NEW VALIDATION METHODS ---
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

class FileUploadForm(forms.Form):
    file = forms.FileField()

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'hod']
        # ADDED: Widget to apply the select2 class
        widgets = {
            'hod': forms.Select(attrs={'class': 'select2-widget', 'style': 'width: 100%'})
        }
    def __init__(self, *args, **kwargs):
        university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)
        if university:
            # --- NEW LOGIC TO EXCLUDE TEACHING FACULTY ---

            # 1. Get the primary keys of all faculty members who are teaching a subject.
            # The 'subjects_taught' is the related_name from the ManyToManyField on the Subject model.
            teaching_faculty_ids = Faculty.objects.filter(
                subjects_taught__isnull=False
            ).values_list('pk', flat=True).distinct()

            # 2. Start with the base queryset of all faculty in the university.
            queryset = Faculty.objects.filter(university=university)
            
            # 3. Exclude the faculty members who are actively teaching.
            self.fields['hod'].queryset = queryset.exclude(pk__in=teaching_faculty_ids)


class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['submitted_file']
        widgets = {
            'submitted_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
class GradingForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['grade', 'feedback']
        widgets = {
            'grade': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Grade'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': 'Feedback...'}),
        }
    
class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'marks']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'question_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_question_type'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Create a formset for MCQ Options linked to a Question
MCQOptionFormSet = inlineformset_factory(
    Question,       # Parent model
    MCQOption,      # Child model
    fields=('text', 'is_correct'), # Fields to include
    extra=4,        # Number of empty forms to display
    can_delete=False, # We don't need to delete options from this form
    widgets={
        'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option text'}),
    }
)

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'due_date', 'total_marks']
        widgets = {
            'due_date': forms.DateTimeInput(
                attrs={'class': 'form-control datetimepicker', 'placeholder': 'Select a date and time'}
            ),
        }

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'due_date']
        widgets = {
            'due_date': forms.DateTimeInput(
                attrs={'class': 'form-control datetimepicker', 'placeholder': 'Select a date and time'}
            ),
        }
    
class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['title', 'code', 'faculty']
        widgets = {
            # This applies the Select2 widget to the faculty multi-select field
            'faculty': forms.SelectMultiple(attrs={'class': 'select2-widget', 'style': 'width: 100%'})
        }

    def __init__(self, *args, **kwargs):
        # Pop the university from kwargs, passed from the view
        university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)

        if university:
            # Get the primary keys of all faculty who are HODs in this university
            hod_ids = Department.objects.filter(
                university=university, 
                hod__isnull=False
            ).values_list('hod__pk', flat=True)

            # Set the queryset for the 'faculty' field to:
            # - Filter by the correct university
            # - Exclude any faculty member who is an HOD
            self.fields['faculty'].queryset = Faculty.objects.filter(
                university=university
            ).exclude(
                pk__in=hod_ids
            )