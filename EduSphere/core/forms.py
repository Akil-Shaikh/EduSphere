# core/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import AssignmentSubmission,Question,MCQOption

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