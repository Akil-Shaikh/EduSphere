# core/views.py

from django.shortcuts import redirect,render,get_object_or_404
from django.views.generic import FormView,TemplateView
from django.urls import reverse_lazy # Use reverse_lazy for class attributes
from django.views.generic.edit import CreateView, UpdateView , DeleteView, FormMixin # Import editing views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, DetailView # Add DetailView
from .models import Course, Department, Subject, Student, Enrollment, LearningResource,Assignment,AssignmentSubmission,Quiz,Question,MCQOption,QuizAttempt,StudentAnswer
from .forms import AssignmentSubmissionForm,GradingForm,QuestionForm,MCQOptionFormSet
from django import forms
from django.forms import modelformset_factory
from django.views import View
from django.db import models

class StudentRequiredMixin(UserPassesTestMixin):
    """Verify that the current user is a Student."""
    def test_func(self):
        return self.request.user.is_authenticated and hasattr(self.request.user, 'student')

class FacultyRequiredMixin(UserPassesTestMixin):
    """Verify that the current user is a Faculty member."""
    def test_func(self):
        # We also check that the user is not an HOD, as we might want
        # separate views for them later. For now, an HOD is also a faculty member.
        return self.request.user.is_authenticated and hasattr(self.request.user, 'faculty')
    
# ... HODRequiredMixin and DashboardView remain the same ...
class HODRequiredMixin(UserPassesTestMixin):
    """Verify that the current user is an HOD."""
    def test_func(self):
        return self.request.user.is_authenticated and hasattr(self.request.user, 'faculty') and Department.objects.filter(hod=self.request.user.faculty).exists()

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        # ... (code from previous step)
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if hasattr(user, 'student'):
            context['role'] = 'Student'
        elif hasattr(user, 'faculty'):
            if Department.objects.filter(hod=user.faculty).exists():
                context['role'] = 'Head of Department'
            else:
                context['role'] = 'Faculty'
        elif hasattr(user, 'universityadmin'):
            context['role'] = 'University Admin'
        else:
            context['role'] = 'User'
            
        return context

class HODCourseListView(LoginRequiredMixin, HODRequiredMixin, ListView):
    # ... (code from previous step remains the same)
    model = Course
    template_name = 'core/hod_course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Course.objects.filter(department=hods_department).order_by('code')

# --- NEW VIEWS START HERE ---

class CourseCreateView(LoginRequiredMixin, HODRequiredMixin, CreateView):
    model = Course
    fields = ['title', 'code'] # Fields the HOD can fill in
    template_name = 'core/course_form.html'
    success_url = reverse_lazy('core:hod_course_list')

    def form_valid(self, form):
        # Automatically set the department to the HOD's department.
        # This is crucial for security and data integrity.
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        form.instance.department = hods_department
        return super().form_valid(form)

class CourseUpdateView(LoginRequiredMixin, HODRequiredMixin, UpdateView):
    model = Course
    fields = ['title', 'code'] # Fields the HOD can edit
    template_name = 'core/course_form.html'
    success_url = reverse_lazy('core:hod_course_list')

    def get_queryset(self):
        # Ensure HOD can only edit courses within their own department.
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Course.objects.filter(department=hods_department)
    
class CourseDetailView(LoginRequiredMixin, HODRequiredMixin, DetailView):
    model = Course
    template_name = 'core/course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        # Ensure HOD can only view details of courses in their own department
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Course.objects.filter(department=hods_department)

class SubjectCreateView(LoginRequiredMixin, HODRequiredMixin, CreateView):
    model = Subject
    fields = ['title', 'code', 'faculty']
    template_name = 'core/subject_form.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter faculty queryset to only show faculty from the same university
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        form.fields['faculty'].queryset = hods_department.faculty_members.all()
        return form

    def form_valid(self, form):
        # Assign the subject to the correct course from the URL
        course = Course.objects.get(pk=self.kwargs['course_pk'])
        form.instance.course = course
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect back to the course detail page after creation
        return reverse_lazy('core:course_detail', kwargs={'pk': self.kwargs['course_pk']})
    


class EnrollStudentView(LoginRequiredMixin, HODRequiredMixin, CreateView):
    model = Enrollment
    fields = ['student', 'roll_number']
    template_name = 'core/enrollment_form.html'

    def get_context_data(self, **kwargs):
        # Pass the course to the template
        context = super().get_context_data(**kwargs)
        context['course'] = Course.objects.get(pk=self.kwargs['course_pk'])
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter the 'student' dropdown
        course_pk = self.kwargs['course_pk']
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        
        # Get primary keys of students already enrolled in this course
        enrolled_student_pks = Enrollment.objects.filter(course__pk=course_pk).values_list('student__pk', flat=True)
        
        # Filter queryset to students in the same university, excluding those already enrolled
        form.fields['student'].queryset = Student.objects.filter(
            university=hods_department.university
        ).exclude(
            pk__in=enrolled_student_pks
        )
        return form

    def form_valid(self, form):
        # Assign the enrollment to the correct course from the URL
        course = Course.objects.get(pk=self.kwargs['course_pk'])
        form.instance.course = course
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect back to the course detail page
        return reverse_lazy('core:course_detail', kwargs={'pk': self.kwargs['course_pk']})


class StudentCourseListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    model = Course
    template_name = 'core/student_course_list.html'
    context_object_name = 'enrolled_courses'

    def get_queryset(self):
        """
        Return only the courses the logged-in student is enrolled in.
        """
        # The 'student' profile is related to the User model one-to-one.
        # The 'enrolled_courses' is the ManyToManyField on the Student model.
        student_profile = self.request.user.student
        return student_profile.enrolled_courses.all().order_by('code')

class StudentCourseDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    model = Course
    template_name = 'core/student_course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        """
        Security Check: A student can only view the details of a course
        they are enrolled in.
        """
        return self.request.user.student.enrolled_courses.all()

class StudentTranscriptView(LoginRequiredMixin, StudentRequiredMixin, TemplateView):
    template_name = 'core/student_transcript.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student

        # Get all courses the student is enrolled in
        enrolled_courses = student.enrolled_courses.prefetch_related(
            'subjects__assignments__submissions',
            'subjects__quizzes__attempts'
        ).all()

        transcript_data = []
        for course in enrolled_courses:
            course_data = {
                'course': course,
                'subjects': []
            }
            for subject in course.subjects.all():
                # Get graded assignments for this student in this subject
                assignments = AssignmentSubmission.objects.filter(
                    assignment__subject=subject,
                    student=student,
                    grade__isnull=False # Only show graded assignments
                )
                
                # Get quiz attempts for this student in this subject
                quizzes = QuizAttempt.objects.filter(
                    quiz__subject=subject,
                    student=student
                )

                if assignments.exists() or quizzes.exists():
                    course_data['subjects'].append({
                        'subject': subject,
                        'assignments': assignments,
                        'quizzes': quizzes,
                    })
            
            if course_data['subjects']:
                transcript_data.append(course_data)
        
        context['transcript_data'] = transcript_data
        return context
    
class StudentAssignmentDetailView(LoginRequiredMixin, StudentRequiredMixin, FormMixin, DetailView):
    model = Assignment
    form_class = AssignmentSubmissionForm
    template_name = 'core/student_assignment_detail.html'
    context_object_name = 'assignment'

    def get_queryset(self):
        """Security: A student can only view assignments for courses they are enrolled in."""
        return Assignment.objects.filter(subject__course__students=self.request.user.student)

    def get_context_data(self, **kwargs):
        """Add the form and any existing submission to the context."""
        context = super().get_context_data(**kwargs)
        # Check for an existing submission
        existing_submission = AssignmentSubmission.objects.filter(
            assignment=self.object,
            student=self.request.user.student
        ).first()
        context['existing_submission'] = existing_submission
        # Only add the form if there is no existing submission
        if not existing_submission:
            context['form'] = self.get_form()
        return context

    def post(self, request, *args, **kwargs):
        """Handle form submission."""
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        """Save the new submission."""
        submission = form.save(commit=False)
        submission.student = self.request.user.student
        submission.assignment = self.object
        submission.save()
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect back to the same page to show the submission status."""
        return reverse_lazy('core:student_assignment_detail', kwargs={'pk': self.object.pk})

class TakeQuizView(LoginRequiredMixin, StudentRequiredMixin, FormView):
    template_name = 'core/quiz_attempt.html'

    # --- THIS METHOD IS RENAMED ---
    def get_form_class(self):
        quiz = self.get_quiz()
        # Dynamically create a form class with fields for each question
        form_fields = {}
        for question in quiz.questions.all().order_by('id'):
            field_name = f'question_{question.id}'
            if question.question_type == 'MCQ':
                form_fields[field_name] = forms.ModelChoiceField(
                    queryset=question.options.all(),
                    widget=forms.RadioSelect,
                    label=question.text,
                    required=True,
                )
            elif question.question_type == 'DESCRIPTIVE':
                form_fields[field_name] = forms.CharField(
                    widget=forms.Textarea,
                    label=question.text,
                    required=True,
                )
        return type('QuizForm', (forms.BaseForm,), {'base_fields': form_fields})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = self.get_quiz()
        # We need to add the form instance for GET requests manually now
        # since we are not defining it on the class
        if 'form' not in context:
            context['form'] = self.get_form()
        return context

    def form_valid(self, form):
        quiz = self.get_quiz()
        student = self.request.user.student
        
        # Create the main quiz attempt record
        attempt = QuizAttempt.objects.create(quiz=quiz, student=student, score=0)
        
        current_score = 0
        for name, value in form.cleaned_data.items():
            question_id = int(name.split('_')[1])
            question = Question.objects.get(id=question_id)
            
            answer = StudentAnswer(quiz_attempt=attempt, question=question)
            if question.question_type == 'MCQ':
                selected_option = value
                answer.mcq_option = selected_option
                if selected_option.is_correct:
                    current_score += question.marks
            else: # Descriptive
                answer.descriptive_answer = value
            answer.save()
            
        attempt.score = current_score
        attempt.save()
        
        # Store attempt pk in session to pass to success_url
        self.request.session['quiz_attempt_pk'] = attempt.pk
        return super().form_valid(form)

    def get_success_url(self):
        attempt_pk = self.request.session.get('quiz_attempt_pk')
        return reverse_lazy('core:quiz_result', kwargs={'pk': attempt_pk})

    def get_quiz(self):
        return Quiz.objects.get(pk=self.kwargs['pk'])

class QuizResultView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    model = QuizAttempt
    template_name = 'core/quiz_result.html'
    context_object_name = 'attempt'

    def get_queryset(self):
        """Security: Students can only view their own quiz results."""
        return QuizAttempt.objects.filter(student=self.request.user.student)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_marks = sum(q.marks for q in self.object.quiz.questions.all())
        context['total_marks'] = total_marks
        return context
    
class FacultySubjectListView(LoginRequiredMixin, FacultyRequiredMixin, ListView):
    model = Subject
    template_name = 'core/faculty_subject_list.html'
    context_object_name = 'subjects_taught'

    def get_queryset(self):
        """
        Return only the subjects the logged-in faculty member is assigned to teach.
        """
        # The 'faculty' profile is related to the User model one-to-one.
        # The 'subjects_taught' is the ManyToManyField on the Faculty model.
        faculty_profile = self.request.user.faculty
        return faculty_profile.subjects_taught.all().order_by('course__code', 'code')
class FacultySubjectDetailView(LoginRequiredMixin, FacultyRequiredMixin, DetailView):
    model = Subject
    template_name = 'core/faculty_subject_detail.html'
    context_object_name = 'subject'

    def get_queryset(self):
        """
        Security check: Ensures the logged-in faculty can only access
        subjects they are assigned to.
        """
        return self.request.user.faculty.subjects_taught.all()

class ResourceCreateView(LoginRequiredMixin, FacultyRequiredMixin, CreateView):
    model = LearningResource
    fields = ['title', 'description', 'file', 'link']
    template_name = 'core/resource_form.html'

    def get_context_data(self, **kwargs):
        # Pass the subject to the template for context
        context = super().get_context_data(**kwargs)
        context['subject'] = Subject.objects.get(pk=self.kwargs['subject_pk'])
        return context

    def form_valid(self, form):
        # Assign the resource to the correct subject from the URL
        subject = Subject.objects.get(pk=self.kwargs['subject_pk'])
        form.instance.subject = subject
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect back to the subject detail page
        return reverse_lazy('core:faculty_subject_detail', kwargs={'pk': self.kwargs['subject_pk']})
    
class AssignmentCreateView(LoginRequiredMixin, FacultyRequiredMixin, CreateView):
    model = Assignment
    fields = ['title', 'description', 'due_date', 'total_marks']
    template_name = 'core/assignment_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subject'] = Subject.objects.get(pk=self.kwargs['subject_pk'])
        return context

    def form_valid(self, form):
        subject = Subject.objects.get(pk=self.kwargs['subject_pk'])
        form.instance.subject = subject
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('core:faculty_subject_detail', kwargs={'pk': self.kwargs['subject_pk']})

class AssignmentUpdateView(LoginRequiredMixin, FacultyRequiredMixin, UpdateView):
    model = Assignment
    fields = ['title', 'description', 'due_date', 'total_marks']
    template_name = 'core/assignment_form.html'

    def get_queryset(self):
        """Security: Ensure faculty can only edit assignments in subjects they teach."""
        return Assignment.objects.filter(subject__faculty=self.request.user.faculty)

    def get_success_url(self):
        return reverse_lazy('core:faculty_subject_detail', kwargs={'pk': self.object.subject.pk})

class AssignmentDeleteView(LoginRequiredMixin, FacultyRequiredMixin, DeleteView):
    model = Assignment
    template_name = 'core/assignment_confirm_delete.html'
    
    def get_queryset(self):
        """Security: Ensure faculty can only delete assignments in subjects they teach."""
        return Assignment.objects.filter(subject__faculty=self.request.user.faculty)

    def get_success_url(self):
        return reverse_lazy('core:faculty_subject_detail', kwargs={'pk': self.object.subject.pk})

class SubmissionListView(LoginRequiredMixin, FacultyRequiredMixin, DetailView):
    model = Assignment
    template_name = 'core/submission_list.html'
    context_object_name = 'assignment'

    def get_queryset(self):
        """Security: Ensure faculty can only view submissions for their own assignments."""
        return Assignment.objects.filter(subject__faculty=self.request.user.faculty)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submissions = self.object.submissions.all().order_by('student__user__last_name')
        
        # Create a list of tuples, each containing a submission and its grading form
        submission_forms = []
        for sub in submissions:
            submission_forms.append((sub, GradingForm(instance=sub)))
        
        context['submission_forms'] = submission_forms
        return context

class GradeSubmissionView(LoginRequiredMixin, FacultyRequiredMixin, UpdateView):
    model = AssignmentSubmission
    form_class = GradingForm
    
    def get_queryset(self):
        """Security: Ensure faculty can only grade submissions for their own assignments."""
        return AssignmentSubmission.objects.filter(assignment__subject__faculty=self.request.user.faculty)

    def get_success_url(self):
        """Redirect back to the submission list page."""
        submission = self.get_object()
        return reverse_lazy('core:view_submissions', kwargs={'pk': submission.assignment.pk})
    
class QuizCreateView(LoginRequiredMixin, FacultyRequiredMixin, CreateView):
    model = Quiz
    fields = ['title', 'due_date']
    template_name = 'core/quiz_form.html'

    def form_valid(self, form):
        subject = Subject.objects.get(pk=self.kwargs['subject_pk'])
        form.instance.subject = subject
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subject'] = Subject.objects.get(pk=self.kwargs['subject_pk'])
        return context

    # --- ADD THIS METHOD ---
    def get_success_url(self):
        # Redirect to the detail page of the quiz that was just created.
        # self.object is the new Quiz instance.
        return reverse_lazy('core:quiz_detail', kwargs={'pk': self.object.pk})

class QuizDetailView(LoginRequiredMixin, FacultyRequiredMixin, DetailView):
    # ... (This view is correct) ...
    model = Quiz
    template_name = 'core/quiz_builder.html'
    context_object_name = 'quiz'

    def get_queryset(self):
        return Quiz.objects.filter(subject__faculty=self.request.user.faculty)


class QuizUpdateView(LoginRequiredMixin, FacultyRequiredMixin, UpdateView):
    model = Quiz
    fields = ['title', 'due_date']
    template_name = 'core/quiz_form.html'

    def get_queryset(self):
        return Quiz.objects.filter(subject__faculty=self.request.user.faculty)

    # --- ADD THIS METHOD ---
    def get_success_url(self):
        # Redirect to the detail page of the quiz that was just updated.
        return reverse_lazy('core:quiz_detail', kwargs={'pk': self.object.pk})

class QuizDeleteView(LoginRequiredMixin, FacultyRequiredMixin, DeleteView):
    model = Quiz
    template_name = 'core/quiz_confirm_delete.html'
    
    def get_queryset(self):
        return Quiz.objects.filter(subject__faculty=self.request.user.faculty)

    def get_success_url(self):
        return reverse_lazy('core:faculty_subject_detail', kwargs={'pk': self.object.subject.pk})
    
class QuestionCreateView(LoginRequiredMixin, FacultyRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'core/question_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = Quiz.objects.get(pk=self.kwargs['quiz_pk'])
        if self.request.POST:
            context['option_formset'] = MCQOptionFormSet(self.request.POST)
        else:
            context['option_formset'] = MCQOptionFormSet()
        return context

    def form_valid(self, form):
        # Assign question to the correct quiz
        quiz = Quiz.objects.get(pk=self.kwargs['quiz_pk'])
        form.instance.quiz = quiz
        self.object = form.save() # Save the question to get an ID

        # Process the formset for options
        option_formset = MCQOptionFormSet(self.request.POST, instance=self.object)
        if option_formset.is_valid():
            option_formset.save()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('core:quiz_detail', kwargs={'pk': self.kwargs['quiz_pk']})

class QuizAttemptsListView(LoginRequiredMixin, FacultyRequiredMixin, DetailView):
    model = Quiz
    template_name = 'core/quiz_attempts_list.html'
    context_object_name = 'quiz'

    def get_queryset(self):
        """Security: Faculty can only view attempts for quizzes in their subjects."""
        return Quiz.objects.filter(subject__faculty=self.request.user.faculty)

# core/views.py

class GradeQuizAttemptView(LoginRequiredMixin, FacultyRequiredMixin, View):
    
    def get(self, request, pk):
        attempt = get_object_or_404(QuizAttempt, pk=pk, quiz__subject__faculty=request.user.faculty)
        DescriptiveAnswerFormSet = modelformset_factory(StudentAnswer, fields=('marks_awarded',), extra=0)
        descriptive_answers_qs = attempt.answers.filter(question__question_type='DESCRIPTIVE')
        formset = DescriptiveAnswerFormSet(queryset=descriptive_answers_qs)

        # --- NEW LOGIC HERE ---
        # Pair up questions with their answers for easier rendering in the template
        questions_and_answers = []
        for question in attempt.quiz.questions.all().order_by('id'):
            student_answer = attempt.answers.filter(question=question).first()
            questions_and_answers.append({
                'question': question,
                'answer': student_answer
            })
        
        context = {
            'attempt': attempt,
            'formset': formset,
            'questions_and_answers': questions_and_answers,
        }
        return render(request, 'core/grade_quiz_attempt.html', context)

    def post(self, request, pk):
        # ... The 'post' method from the previous step remains the same ...
        attempt = get_object_or_404(QuizAttempt, pk=pk, quiz__subject__faculty=request.user.faculty)
        DescriptiveAnswerFormSet = modelformset_factory(StudentAnswer, fields=('marks_awarded',), extra=0)
        descriptive_answers_qs = attempt.answers.filter(question__question_type='DESCRIPTIVE')
        formset = DescriptiveAnswerFormSet(request.POST, queryset=descriptive_answers_qs)
        
        if formset.is_valid():
            formset.save()
            
            total_score = attempt.answers.filter(mcq_option__is_correct=True).aggregate(
                total=models.Sum('question__marks')
            )['total'] or 0
            
            # Use the saved formset instances to calculate the sum
            descriptive_score = 0
            for form in formset.cleaned_data:
                 if form.get('marks_awarded'):
                    descriptive_score += form['marks_awarded']

            attempt.score = total_score + descriptive_score
            attempt.save()
            
            return redirect('core:quiz_attempts_list', pk=attempt.quiz.pk)
        
        # We need to rebuild the context if the form is invalid
        questions_and_answers = []
        for question in attempt.quiz.questions.all().order_by('id'):
            student_answer = attempt.answers.filter(question=question).first()
            questions_and_answers.append({
                'question': question,
                'answer': student_answer
            })
        context = {
            'attempt': attempt, 
            'formset': formset,
            'questions_and_answers': questions_and_answers
        }
        return render(request, 'core/grade_quiz_attempt.html', context)
