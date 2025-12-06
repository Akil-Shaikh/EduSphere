

from django import forms
from django.forms import inlineformset_factory
from .models import AssignmentSubmission,Question,MCQOption,Quiz,Assignment , Department, Faculty,Subject,Student
from django.contrib.auth.models import User

class FacultyUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep current password.")

    class Meta:
        model = Faculty
        fields = ['employee_id', 'department']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            
            self.fields['department'].queryset = Department.objects.filter(university=self.instance.university)

    def save(self, commit=True):
        faculty = super().save(commit=commit)
        user = faculty.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return faculty

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

class StudentUpdateForm(forms.ModelForm):
    
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep the current password.")

    class Meta:
        model = Student
        fields = ['student_id'] 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        student = super().save(commit=commit)
        user = student.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return student

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
        
        widgets = {
            'hod': forms.Select(attrs={'class': 'select2-widget', 'style': 'width: 100%'})
        }
    def __init__(self, *args, **kwargs):
        university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)
        if university:
            teaching_faculty_ids = Faculty.objects.filter(
                subjects_taught__isnull=False
            ).values_list('pk', flat=True).distinct()
            queryset = Faculty.objects.filter(university=university)
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
    def clean(self):
        """
        Custom validation to ensure the grade is not higher than the total marks.
        """
        cleaned_data = super().clean()
        grade = cleaned_data.get("grade")
        
        assignment = self.instance.assignment
        total_marks = assignment.total_marks

        if grade is not None and total_marks is not None:
            if grade > total_marks:
                raise forms.ValidationError(
                    f"The grade ({grade}) cannot be greater than the total possible marks ({total_marks})."
                )
        
        return cleaned_data

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'marks']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'question_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_question_type'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control'}),
        }

MCQOptionFormSet = inlineformset_factory(
    Question,       
    MCQOption,      
    fields=('text', 'is_correct'), 
    extra=4,        
    can_delete=False, 
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
            
            'faculty': forms.SelectMultiple(attrs={'class': 'select2-widget', 'style': 'width: 100%'})
        }

    def __init__(self, *args, **kwargs):
        
        university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)

        if university:
            hod_ids = Department.objects.filter(
                university=university, 
                hod__isnull=False
            ).values_list('hod__pk', flat=True)
            self.fields['faculty'].queryset = Faculty.objects.filter(
                university=university
            ).exclude(
                pk__in=hod_ids
            )