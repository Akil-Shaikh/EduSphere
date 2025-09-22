# core/views.py

from django.http import HttpResponseRedirect
from django.shortcuts import redirect,render,get_object_or_404
from django.views.generic import FormView,TemplateView
from django.urls import reverse_lazy # Use reverse_lazy for class attributes
from django.views.generic.edit import CreateView, UpdateView , DeleteView, FormMixin # Import editing views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, DetailView # Add DetailView
from .models import Course, Department, Subject, Student,Faculty, Enrollment, LearningResource,Assignment,Notification,AssignmentSubmission,Quiz,Question,MCQOption,QuizAttempt,StudentAnswer
from .forms import FileUploadForm,AssignmentSubmissionForm,FacultyRegistrationForm,GradingForm,QuestionForm,MCQOptionFormSet,AssignmentForm,QuizForm,DepartmentForm,StudentRegistrationForm, SubjectForm
from django import forms
from django.forms import modelformset_factory
from django.views import View
from django.contrib import messages
from django.db import models,transaction
from django.contrib.auth.models import User 
import csv
import io


class UniversityAdminRequiredMixin(UserPassesTestMixin):
    """Verify that the current user is a University Admin."""
    def test_func(self):
        return self.request.user.is_authenticated and hasattr(self.request.user, 'universityadmin')

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
    """
    Handles user redirection based on their role upon login or visiting the root URL.
    """
    template_name = 'core/dashboard.html' # Fallback for unassigned users

    def get(self, request, *args, **kwargs):
        user = request.user

        # 1. Check if the user is a superuser and redirect to the admin panel
        if user.is_superuser:
            return redirect('admin:index')

        # 2. Check for other roles in order of precedence
        if hasattr(user, 'universityadmin'):
            return redirect('core:uni_admin_dashboard')
        
        if hasattr(user, 'faculty') and Department.objects.filter(hod=user.faculty).exists():
            return redirect('core:hod_course_list')

        if hasattr(user, 'faculty'):
            return redirect('core:faculty_subject_list')

        if hasattr(user, 'student'):
            return redirect('core:student_course_list')
        
        # 3. If no specific role is found, show a generic page
        context = self.get_context_data(**kwargs)
        context['role'] = 'Unassigned User'
        return self.render_to_response(context)


class UniversityAdminDashboardView(LoginRequiredMixin, UniversityAdminRequiredMixin, TemplateView):
    template_name = 'core/u_admin_dashboard.html'

class DepartmentListView(LoginRequiredMixin, UniversityAdminRequiredMixin, ListView):
    model = Department
    template_name = 'core/department_list.html'
    context_object_name = 'departments'

    def get_queryset(self):
        # Filter departments to the admin's university
        return Department.objects.filter(university=self.request.user.universityadmin.university)

class DepartmentCreateView(LoginRequiredMixin, UniversityAdminRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'core/department_form.html'
    success_url = reverse_lazy('core:department_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass the admin's university to the form
        kwargs['university'] = self.request.user.universityadmin.university
        return kwargs

    def form_valid(self, form):
        # Automatically set the new department's university
        form.instance.university = self.request.user.universityadmin.university
        messages.success(self.request, "Department created successfully.")
        return super().form_valid(form)

class DepartmentUpdateView(LoginRequiredMixin, UniversityAdminRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'core/department_form.html'
    success_url = reverse_lazy('core:department_list')

    def get_queryset(self):
        # Ensure admin can only edit departments in their own university
        return Department.objects.filter(university=self.request.user.universityadmin.university)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['university'] = self.request.user.universityadmin.university
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Department updated successfully.")
        return super().form_valid(form)
class FacultyListView(LoginRequiredMixin, UniversityAdminRequiredMixin, ListView):
    model = Faculty
    template_name = 'core/faculty_list.html'
    context_object_name = 'faculty_members'

    def get_queryset(self):
        return Faculty.objects.filter(university=self.request.user.universityadmin.university)

class FacultyRegistrationView(LoginRequiredMixin, UniversityAdminRequiredMixin, View):
    form_class = FacultyRegistrationForm
    template_name = 'core/faculty_registration_form.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class(university=request.user.universityadmin.university)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, university=request.user.universityadmin.university)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user_data = {
                        'username': form.cleaned_data['username'],
                        'first_name': form.cleaned_data['first_name'],
                        'last_name': form.cleaned_data['last_name'],
                        'email': form.cleaned_data['email'],
                        'password': form.cleaned_data['password'],
                    }
                    user = User.objects.create_user(**user_data)
                    
                    Faculty.objects.create(
                        user=user,
                        employee_id=form.cleaned_data['employee_id'],
                        department=form.cleaned_data['department'],
                        university=request.user.universityadmin.university
                    )
                
                messages.success(request, f"Faculty '{user.username}' registered successfully.")
                return redirect('core:faculty_list')
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")

        return render(request, self.template_name, {'form': form})

class StudentListView(LoginRequiredMixin, UniversityAdminRequiredMixin, ListView):
    model = Student
    template_name = 'core/student_list.html'
    context_object_name = 'students'

    def get_queryset(self):
        # Filter students to the admin's university
        return Student.objects.filter(university=self.request.user.universityadmin.university)

class StudentRegistrationView(LoginRequiredMixin, UniversityAdminRequiredMixin, View):
    form_class = StudentRegistrationForm
    template_name = 'core/student_registration_form.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            try:
                # Use a transaction to ensure both User and Student are created
                with transaction.atomic():
                    user_data = form.cleaned_data
                    student_id = user_data.pop('student_id')
                    
                    # create_user handles password hashing
                    user = User.objects.create_user(**user_data)
                    
                    # Create the student profile
                    Student.objects.create(
                        user=user,
                        student_id=student_id,
                        university=request.user.universityadmin.university
                    )
                
                messages.success(request, f"Student '{user.username}' registered successfully.")
                return redirect('core:student_list')
            except Exception as e:
                # If anything goes wrong, the transaction will roll back
                messages.error(request, f"An error occurred: {e}")

        return render(request, self.template_name, {'form': form})
class StudentBulkRegistrationView(LoginRequiredMixin, UniversityAdminRequiredMixin, View):
    template_name = 'core/student_bulk_register.html'

    def get(self, request, *args, **kwargs):
        form = FileUploadForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            
            # Check if it's a CSV file
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'This is not a CSV file.')
                return render(request, self.template_name, {'form': form})

            # Process the CSV file
            try:
                with transaction.atomic(): # Use a transaction
                    # Read the file in memory
                    data_set = csv_file.read().decode('UTF-8')
                    io_string = io.StringIO(data_set)
                    # Skip the header
                    next(io_string)
                    
                    created_count = 0
                    for column in csv.reader(io_string, delimiter=',', quotechar='"'):
                        # Assumes CSV columns are: username,password,first_name,last_name,email,student_id
                        user = User.objects.create_user(
                            username=column[0],
                            password=column[1],
                            first_name=column[2],
                            last_name=column[3],
                            email=column[4]
                        )
                        Student.objects.create(
                            user=user,
                            student_id=column[5],
                            university=request.user.universityadmin.university
                        )
                        created_count += 1
                
                messages.success(request, f'Successfully registered {created_count} new students.')
                return redirect('core:student_list')

            except Exception as e:
                # If any error occurs, the transaction will be rolled back.
                messages.error(request, f"An error occurred while processing the file: {e}")

        return render(request, self.template_name, {'form': form})

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
        response = super().form_valid(form)

        # NEW: Add a success message
        messages.success(self.request, f"Course '{self.object.title}' created successfully.")

        return response

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

class CourseDeleteView(LoginRequiredMixin, HODRequiredMixin, DeleteView):
    model = Course
    template_name = 'core/course_confirm_delete.html'
    success_url = reverse_lazy('core:hod_course_list')

    def get_queryset(self):
        # Ensure HOD can only delete courses within their own department
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Course.objects.filter(department=hods_department)

class SubjectCreateView(LoginRequiredMixin, HODRequiredMixin, CreateView):
    model = Subject
    # fields = ['title', 'code', 'faculty'] # Remove this line
    form_class = SubjectForm # Use our custom form
    template_name = 'core/subject_form.html'

    def get_form_kwargs(self):
        # Pass the HOD's university to the form
        kwargs = super().get_form_kwargs()
        kwargs['university'] = self.request.user.faculty.university
        return kwargs

    def form_valid(self, form):
        # ... this method remains the same ...
        course = Course.objects.get(pk=self.kwargs['course_pk'])
        form.instance.course = course
        return super().form_valid(form)

    def get_success_url(self):
        # ... this method remains the same ...
        return reverse_lazy('core:course_detail', kwargs={'pk': self.kwargs['course_pk']})

class SubjectUpdateView(LoginRequiredMixin, HODRequiredMixin, UpdateView):
    model = Subject
    form_class = SubjectForm # Already using this, which is good
    template_name = 'core/subject_form.html'

    def get_form_kwargs(self):
        # Pass the subject's university to the form
        kwargs = super().get_form_kwargs()
        # The object being updated is self.object
        kwargs['university'] = self.get_object().course.university
        return kwargs

    def get_queryset(self):
        # ... this method remains the same ...
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Subject.objects.filter(course__department=hods_department)

    def get_success_url(self):
        # ... this method remains the same ...
        return reverse_lazy('core:course_detail', kwargs={'pk': self.object.course.pk})

class SubjectDeleteView(LoginRequiredMixin, HODRequiredMixin, DeleteView):
    model = Subject
    template_name = 'core/subject_confirm_delete.html'

    def get_queryset(self):
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Subject.objects.filter(course__department=hods_department)

    def get_success_url(self):
        return reverse_lazy('core:course_detail', kwargs={'pk': self.object.course.pk})

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

class StudentBulkEnrollmentView(LoginRequiredMixin, HODRequiredMixin, View):
    template_name = 'core/student_bulk_enroll.html'

    def get(self, request, *args, **kwargs):
        form = FileUploadForm()
        course = get_object_or_404(Course, pk=self.kwargs['course_pk'])
        return render(request, self.template_name, {'form': form, 'course': course})

    def post(self, request, *args, **kwargs):
        form = FileUploadForm(request.POST, request.FILES)
        course = get_object_or_404(Course, pk=self.kwargs['course_pk'])

        if form.is_valid():
            csv_file = request.FILES['file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Error: This is not a CSV file.')
                return render(request, self.template_name, {'form': form, 'course': course})

            # Process the CSV file
            success_count = 0
            error_list = []
            
            try:
                with transaction.atomic(): # Ensures all-or-nothing enrollment
                    data_set = csv_file.read().decode('UTF-8')
                    io_string = io.StringIO(data_set)
                    next(io_string) # Skip the header row
                    
                    # Get IDs of students already enrolled to prevent duplicates
                    already_enrolled_ids = set(course.students.values_list('student_id', flat=True))
                    
                    for row_num, column in enumerate(csv.reader(io_string), 2): # Start counting from row 2
                        student_id = column[0].strip()
                        roll_number = column[1].strip()

                        if student_id in already_enrolled_ids:
                            continue # Skip already enrolled students silently

                        try:
                            student = Student.objects.get(
                                student_id=student_id,
                                university=course.university
                            )
                            Enrollment.objects.create(
                                student=student,
                                course=course,
                                roll_number=roll_number
                            )
                            success_count += 1
                        except Student.DoesNotExist:
                            error_list.append(f"Row {row_num}: Student with ID '{student_id}' not found in this university.")
                
                if error_list:
                    # If any student was not found, the transaction is rolled back.
                    raise Exception(f"The following errors occurred: {', '.join(error_list)}")
                
                messages.success(request, f'Successfully enrolled {success_count} new students.')
                return redirect('core:course_detail', pk=course.pk)

            except Exception as e:
                messages.error(request, f"Upload failed. No students were enrolled. Error: {e}")

        return render(request, self.template_name, {'form': form, 'course': course})

class UnenrollStudentView(LoginRequiredMixin, HODRequiredMixin, DeleteView):
    model = Enrollment
    template_name = 'core/unenroll_confirm.html'
    context_object_name = 'enrollment'

    def get_queryset(self):
        # Security: Ensure HOD can only unenroll students from courses in their department
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Enrollment.objects.filter(course__department=hods_department)

    def get_success_url(self):
        # Redirect back to the course detail page after unenrolling
        messages.success(self.request, f"Student '{self.object.student.user.username}' has been unenrolled.")
        return reverse_lazy('core:course_detail', kwargs={'pk': self.object.course.pk})

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

class StudentProfileView(LoginRequiredMixin, StudentRequiredMixin, TemplateView):
    template_name = 'core/student_profile.html'

    def get_context_data(self, **kwargs):
        # A TemplateView doesn't have self.object. 
        # We get the student profile directly from the logged-in user.
        context = super().get_context_data(**kwargs)
        context['student_profile'] = self.request.user.student
        return context

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
    def dispatch(self, request, *args, **kwargs):
        quiz = self.get_quiz()
        student = request.user.student
        
        # Check if an attempt already exists for this quiz and student
        existing_attempt = QuizAttempt.objects.filter(quiz=quiz, student=student).first()
        
        if existing_attempt:
            # If an attempt exists, show an info message and redirect to the result page
            messages.info(request, "You have already completed this quiz. Here are your results.")
            return redirect('core:quiz_result', pk=existing_attempt.pk)
            
        # If no attempt exists, proceed as normal
        return super().dispatch(request, *args, **kwargs)
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
    form_class = AssignmentForm
    template_name = 'core/assignment_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subject'] = Subject.objects.get(pk=self.kwargs['subject_pk'])
        return context

    def form_valid(self, form):
        # 1. Create the object in memory, but don't save to DB yet
        self.object = form.save(commit=False)
        
        # 2. Get the subject from the URL and attach it
        subject = Subject.objects.get(pk=self.kwargs['subject_pk'])
        self.object.subject = subject
        
        # 3. Now, save the object to the database
        self.object.save()
        
        # 4. Proceed with notification logic
        course = self.object.subject.course
        students = course.students.all()
        for student_profile in students:
            Notification.objects.create(
                recipient=student_profile.user,
                message=f"A new assignment '{self.object.title}' has been posted for your course '{course.title}'."
            )
        
        messages.success(self.request, "Assignment created and students notified.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('core:faculty_subject_detail', kwargs={'pk': self.kwargs['subject_pk']})

class AssignmentUpdateView(LoginRequiredMixin, FacultyRequiredMixin, UpdateView):
    model = Assignment
    # fields = ['title', 'description', 'due_date', 'total_marks']
    form_class=AssignmentForm
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
    def form_valid(self, form):
        # NEW: Create notification for the student
        submission = self.get_object()
        Notification.objects.create(
            recipient=submission.student.user,
            message=f"Your submission for '{submission.assignment.title}' has been graded. You received {form.cleaned_data.get('grade')}."
        )
        messages.success(self.request, "Grade saved and student notified.")
        return super().form_valid(form)
    
class QuizCreateView(LoginRequiredMixin, FacultyRequiredMixin, CreateView):
    model = Quiz
    # fields = ['title', 'due_date']
    form_class=QuizForm
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
    # fields = ['title', 'due_date']
    form_class=QuizForm
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
            messages.success(request, f"Successfully graded quiz for {attempt.student.user.get_full_name()}.")
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

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'core/notification_list.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        # Get notifications for the current user
        queryset = super().get_queryset().filter(recipient=self.request.user)
        # Mark them as read
        queryset.filter(is_read=False).update(is_read=True)
        return queryset