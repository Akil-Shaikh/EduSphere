# academics/forms.py
from django import forms
from .models import Module,Content

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        # We only need the user to input the title.
        # The 'course' and 'order' will be set automatically in the view.
        fields = ['title']
        


# Add this new form
class ContentForm(forms.ModelForm):
    class Meta:
        model = Content
        # We need fields for all possible content types
        # The view will handle setting the 'module' and 'order'
        fields = ['title', 'content_type', 'text_content', 'file_content', 'video_url']