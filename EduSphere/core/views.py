

from datetime import timedelta
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.shortcuts import redirect,render,get_object_or_404
from django.views.generic import FormView,TemplateView
from django.urls import reverse_lazy 
from django.views.generic.edit import CreateView, UpdateView , DeleteView, FormMixin 
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, DetailView 
from .models import Course, Department, Subject, Student,Faculty, Enrollment, LearningResource,Assignment,Notification,AssignmentSubmission,Quiz,Question,MCQOption,QuizAttempt,StudentAnswer
from .forms import FileUploadForm,FacultyUpdateForm,AssignmentSubmissionForm,StudentUpdateForm,FacultyRegistrationForm,GradingForm,QuestionForm,MCQOptionFormSet,AssignmentForm,QuizForm,DepartmentForm,StudentRegistrationForm, SubjectForm
from django import forms
from django.forms import modelformset_factory
from django.views import View
from django.contrib import messages
from django.db import models,transaction
from django.db.models import Count,Q
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
        return self.request.user.is_authenticated and hasattr(self.request.user, 'faculty')
    

class HODRequiredMixin(UserPassesTestMixin):
    """Verify that the current user is an HOD."""
    def test_func(self):
        return self.request.user.is_authenticated and hasattr(self.request.user, 'faculty') and Department.objects.filter(hod=self.request.user.faculty).exists()


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Handles user redirection based on their role upon login or visiting the root URL.
    """
    template_name = 'core/dashboard.html'

    def get(self, request, *args, **kwargs):
        user = request.user

        if user.is_superuser:
            return redirect('admin:index')

        if hasattr(user, 'universityadmin'):
            return redirect('core:uni_admin_dashboard')
        
        if hasattr(user, 'faculty') and Department.objects.filter(hod=user.faculty).exists():
            return redirect('core:hod_course_list')

        if hasattr(user, 'faculty'):
            return redirect('core:faculty_dashboard')

        if hasattr(user, 'student'):
            return redirect('core:student_course_list')

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
        return Department.objects.filter(university=self.request.user.universityadmin.university)

class DepartmentCreateView(LoginRequiredMixin, UniversityAdminRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'core/department_form.html'
    success_url = reverse_lazy('core:department_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
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
    paginate_by = 25

    def get_queryset(self):
        university = self.request.user.universityadmin.university
        queryset = Faculty.objects.filter(university=university).order_by('user__last_name')

        search_query = self.request.GET.get('q', '')
        department_id = self.request.GET.get('department', '')

        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(employee_id__icontains=search_query)
            )
        if department_id:
            queryset = queryset.filter(department__id=department_id)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        university = self.request.user.universityadmin.university
        context['departments'] = Department.objects.filter(university=university)
        context['current_department_id'] = self.request.GET.get('department', '')
        context['current_search_query'] = self.request.GET.get('q', '')
        return context

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

class FacultyUpdateView(LoginRequiredMixin, UniversityAdminRequiredMixin, UpdateView):
    model = Faculty
    form_class = FacultyUpdateForm
    template_name = 'core/faculty_update_form.html'
    success_url = reverse_lazy('core:faculty_list')

    def get_queryset(self):
        return Faculty.objects.filter(university=self.request.user.universityadmin.university)
    
    def form_valid(self, form):
        messages.success(self.request, "Faculty profile updated successfully.")
        return super().form_valid(form)

class StudentListView(LoginRequiredMixin, UniversityAdminRequiredMixin, ListView):
    model = Student
    template_name = 'core/student_list.html'
    context_object_name = 'students'
    paginate_by = 25

    def get_queryset(self):
        university = self.request.user.universityadmin.university
        queryset = Student.objects.filter(university=university).order_by('user__last_name')

        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(student_id__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_search_query'] = self.request.GET.get('q', '')
        return context

class DepartmentDeleteView(LoginRequiredMixin, UniversityAdminRequiredMixin, DeleteView):
    model = Department
    template_name = 'core/department_confirm_delete.html'
    success_url = reverse_lazy('core:department_list')

    def get_queryset(self):
        # Security: Only allow deleting departments in own university
        return Department.objects.filter(university=self.request.user.universityadmin.university)
    
    def form_valid(self, form):
        messages.success(self.request, "Department deleted successfully.")
        return super().form_valid(form)


class FacultyDeleteView(LoginRequiredMixin, UniversityAdminRequiredMixin, DeleteView):
    model = Faculty
    template_name = 'core/faculty_confirm_delete.html'
    success_url = reverse_lazy('core:faculty_list')

    def get_queryset(self):
        return Faculty.objects.filter(university=self.request.user.universityadmin.university)

    def form_valid(self, form):
        # When deleting a Faculty profile, we should also delete the associated User account
        user = self.object.user
        response = super().form_valid(form) # This deletes the Faculty object
        user.delete() # This deletes the User login
        messages.success(self.request, "Faculty member and user account deleted successfully.")
        return response


class StudentDeleteView(LoginRequiredMixin, UniversityAdminRequiredMixin, DeleteView):
    model = Student
    template_name = 'core/student_confirm_delete.html'
    success_url = reverse_lazy('core:student_list')

    def get_queryset(self):
        return Student.objects.filter(university=self.request.user.universityadmin.university)

    def form_valid(self, form):
        # When deleting a Student profile, we should also delete the associated User account
        user = self.object.user
        response = super().form_valid(form)
        user.delete()
        messages.success(self.request, "Student profile and user account deleted successfully.")
        return response

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
                with transaction.atomic():
                    user_data = form.cleaned_data
                    student_id = user_data.pop('student_id')
                    user = User.objects.create_user(**user_data)
                    Student.objects.create(
                        user=user,
                        student_id=student_id,
                        university=request.user.universityadmin.university
                    )
                
                messages.success(request, f"Student '{user.username}' registered successfully.")
                return redirect('core:student_list')
            except Exception as e:
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
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'This is not a CSV file.')
                return render(request, self.template_name, {'form': form})

            try:
                with transaction.atomic():
                    data_set = csv_file.read().decode('UTF-8')
                    io_string = io.StringIO(data_set)
                    next(io_string)
                    created_count = 0
                    for column in csv.reader(io_string, delimiter=',', quotechar='"'):
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
                messages.error(request, f"An error occurred while processing the file: {e}")

        return render(request, self.template_name, {'form': form})

class HODCourseListView(LoginRequiredMixin, HODRequiredMixin, ListView):
    model = Course
    template_name = 'core/hod_course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Course.objects.filter(department=hods_department).order_by('code')


class CourseCreateView(LoginRequiredMixin, HODRequiredMixin, CreateView):
    model = Course
    fields = ['title', 'code']
    template_name = 'core/course_form.html'
    success_url = reverse_lazy('core:hod_course_list')

    def form_valid(self, form):
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        form.instance.department = hods_department
        form.instance.university = hods_department.university
        response = super().form_valid(form)
        messages.success(self.request, f"Course '{self.object.title}' created successfully.")

        return response

class CourseUpdateView(LoginRequiredMixin, HODRequiredMixin, UpdateView):
    model = Course
    fields = ['title', 'code']
    template_name = 'core/course_form.html'
    success_url = reverse_lazy('core:hod_course_list')

    def get_queryset(self):
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Course.objects.filter(department=hods_department)
    
class CourseDetailView(LoginRequiredMixin, HODRequiredMixin, DetailView):
    model = Course
    template_name = 'core/course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Course.objects.filter(department=hods_department)

    def get_context_data(self, **kwargs):
        """
        Adds the filtered list of enrollments to the context.
        """
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        search_query = self.request.GET.get('q', '')
        
        enrollments = Enrollment.objects.filter(course=course).order_by('student__user__last_name')
        
        if search_query:
            enrollments = enrollments.filter(
                Q(student__user__first_name__icontains=search_query) |
                Q(student__user__last_name__icontains=search_query) |
                Q(student__student_id__icontains=search_query) |
                Q(roll_number__icontains=search_query)
            )
        
        context['enrollments'] = enrollments
        context['current_search_query'] = search_query
        return context

class CourseDeleteView(LoginRequiredMixin, HODRequiredMixin, DeleteView):
    model = Course
    template_name = 'core/course_confirm_delete.html'
    success_url = reverse_lazy('core:hod_course_list')

    def get_queryset(self):
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Course.objects.filter(department=hods_department)

class SubjectCreateView(LoginRequiredMixin, HODRequiredMixin, CreateView):
    model = Subject
    form_class = SubjectForm 
    template_name = 'core/subject_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['university'] = self.request.user.faculty.university
        return kwargs

    def form_valid(self, form):
        course = Course.objects.get(pk=self.kwargs['course_pk'])
        form.instance.course = course
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('core:course_detail', kwargs={'pk': self.kwargs['course_pk']})

class SubjectUpdateView(LoginRequiredMixin, HODRequiredMixin, UpdateView):
    model = Subject
    form_class = SubjectForm 
    template_name = 'core/subject_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['university'] = self.get_object().course.university
        return kwargs

    def get_queryset(self):
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Subject.objects.filter(course__department=hods_department)

    def get_success_url(self):
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
        context = super().get_context_data(**kwargs)
        context['course'] = Course.objects.get(pk=self.kwargs['course_pk'])
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        course_pk = self.kwargs['course_pk']
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        
        enrolled_student_pks = Enrollment.objects.filter(course__pk=course_pk).values_list('student__pk', flat=True)
        
        form.fields['student'].queryset = Student.objects.filter(
            university=hods_department.university
        ).exclude(
            pk__in=enrolled_student_pks
        )
        return form

    def form_valid(self, form):
        course = Course.objects.get(pk=self.kwargs['course_pk'])
        form.instance.course = course
        enrollment = form.save() 

        Notification.objects.create(
            recipient=enrollment.student.user,
            message=f"You have been enrolled in the course '{course.title}'."
        )
        messages.success(self.request, f"Successfully enrolled {enrollment.student.user.username}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('core:course_detail', kwargs={'pk': self.kwargs['course_pk']})

class StudentUpdateView(LoginRequiredMixin, UniversityAdminRequiredMixin, UpdateView):
    model = Student
    form_class = StudentUpdateForm
    template_name = 'core/student_update_form.html'
    success_url = reverse_lazy('core:student_list')

    def get_queryset(self):
        return Student.objects.filter(university=self.request.user.universityadmin.university)
    
    def form_valid(self, form):
        messages.success(self.request, "Student profile updated successfully.")
        return super().form_valid(form)

class StudentBulkEnrollmentView(LoginRequiredMixin, HODRequiredMixin, View):
    """
    Handles the bulk enrollment of students into a course via a CSV file upload.
    """
    template_name = 'core/student_bulk_enroll.html'

    def get(self, request, *args, **kwargs):
        """Displays the file upload form."""
        form = FileUploadForm()
        course = get_object_or_404(Course, pk=self.kwargs['course_pk'])
        return render(request, self.template_name, {'form': form, 'course': course})

    def post(self, request, *args, **kwargs):
        """Processes the uploaded CSV file."""
        form = FileUploadForm(request.POST, request.FILES)
        course = get_object_or_404(Course, pk=self.kwargs['course_pk'])

        if form.is_valid():
            csv_file = request.FILES['file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Error: This is not a CSV file.')
                return render(request, self.template_name, {'form': form, 'course': course})

            success_count = 0
            error_list = []
            
            try:
                with transaction.atomic():
                    data_set = csv_file.read().decode('UTF-8')
                    io_string = io.StringIO(data_set)
                    next(io_string)  
                    
                    already_enrolled_ids = set(course.students.values_list('student_id', flat=True))
                    
                    for row_num, column in enumerate(csv.reader(io_string), 2): 
                        student_id = column[0].strip()
                        roll_number = column[1].strip()

                        if not student_id or not roll_number:
                            error_list.append(f"Row {row_num}: Contains empty values.")
                            continue

                        if student_id in already_enrolled_ids:
                            continue  

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
                            Notification.objects.create(
                                recipient=student.user,
                                message=f"You have been enrolled in the course '{course.title}'."
                            )
                            success_count += 1
                        except Student.DoesNotExist:
                            error_list.append(f"Row {row_num}: Student with ID '{student_id}' not found in this university.")
                
                if error_list:
                    raise Exception("The file contains invalid data.")
                
                messages.success(request, f'Successfully enrolled {success_count} new students and sent notifications.')
                return redirect('core:course_detail', pk=course.pk)

            except Exception:
                error_summary = " ".join(error_list)
                messages.error(request, f"Upload failed. No students were enrolled. Errors: {error_summary}")

        return render(request, self.template_name, {'form': form, 'course': course})

class UnenrollStudentView(LoginRequiredMixin, HODRequiredMixin, DeleteView):
    model = Enrollment
    template_name = 'core/unenroll_confirm.html'
    context_object_name = 'enrollment'

    def get_queryset(self):
        hods_department = Department.objects.get(hod=self.request.user.faculty)
        return Enrollment.objects.filter(course__department=hods_department)

    def get_success_url(self):
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
        student_profile = self.request.user.student
        return student_profile.enrolled_courses.all().order_by('code')

class StudentSubjectDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    model = Subject
    template_name = 'core/student_subject_detail.html'
    context_object_name = 'subject'

    def get_queryset(self):
        """Security: A student can only view subjects of courses they are enrolled in."""
        return Subject.objects.filter(course__students=self.request.user.student)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student
        subject = self.get_object()
        
        context['current_time'] = timezone.now()
        context['attempted_quiz_pks'] = set(QuizAttempt.objects.filter(
            student=student, quiz__subject=subject
        ).values_list('quiz__pk', flat=True))
        
        context['attempted_assignment_pks'] = set(AssignmentSubmission.objects.filter(
            student=student, assignment__subject=subject
        ).values_list('assignment__pk', flat=True))
        
        return context

class StudentCourseDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    model = Course
    template_name = 'core/student_course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        return self.request.user.student.enrolled_courses.all()

class StudentProfileView(LoginRequiredMixin, StudentRequiredMixin, TemplateView):
    template_name = 'core/student_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_profile'] = self.request.user.student
        return context

class StudentTranscriptView(LoginRequiredMixin, StudentRequiredMixin, TemplateView):
    template_name = 'core/student_transcript.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student

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
                assignments = AssignmentSubmission.objects.filter(
                    assignment__subject=subject,
                    student=student,
                    grade__isnull=False 
                )
                
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

    def dispatch(self, request, *args, **kwargs):
        assignment = self.get_object()
        student = request.user.student

        submission_exists = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=student
        ).exists()
        
        if assignment.due_date < timezone.now() and not submission_exists:
            messages.error(request, f"The deadline for the assignment '{assignment.title}' has passed. No more submissions are allowed.")
            return redirect('core:student_subject_detail', pk=assignment.subject.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Security: A student can only view assignments for courses they are enrolled in."""
        return Assignment.objects.filter(subject__course__students=self.request.user.student)

    def get_context_data(self, **kwargs):
        """Add the form, submission status, and current time to the context."""
        context = super().get_context_data(**kwargs)
        existing_submission = AssignmentSubmission.objects.filter(
            assignment=self.object,
            student=self.request.user.student
        ).first()
        context['existing_submission'] = existing_submission
        context['current_time'] = timezone.now()
        
        if not existing_submission and self.object.due_date > context['current_time']:
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
        submission = form.save(commit=False)
        submission.student = self.request.user.student
        submission.assignment = self.object
        submission.save()

        for faculty_profile in self.object.subject.faculty.all():
            Notification.objects.create(
                recipient=faculty_profile.user,
                message=f"'{submission.student.user.get_full_name()}' has submitted the assignment '{self.object.title}'."
            )
        messages.success(self.request, "Assignment submitted successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect back to the same page to show the submission status."""
        return reverse_lazy('core:student_assignment_detail', kwargs={'pk': self.object.pk})

class TakeQuizView(LoginRequiredMixin, StudentRequiredMixin, FormView):
    template_name = 'core/quiz_attempt.html'
    def dispatch(self, request, *args, **kwargs):
        quiz = self.get_quiz()
        student = request.user.student
        
        existing_attempt = QuizAttempt.objects.filter(quiz=quiz, student=student).first()
        
        if existing_attempt:
            messages.info(request, "You have already completed this quiz. Here are your results.")
            return redirect('core:quiz_result', pk=existing_attempt.pk)
            
        if quiz.due_date < timezone.now():
            messages.error(request, f"The deadline for the quiz '{quiz.title}' has passed.")
            return redirect('core:student_subject_detail', pk=quiz.subject.pk)
        return super().dispatch(request, *args, **kwargs)
    def get_form_class(self):
        quiz = self.get_quiz()
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
        if 'form' not in context:
            context['form'] = self.get_form()
        return context

    def form_valid(self, form):
        quiz = self.get_quiz()
        student = self.request.user.student
        
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
            else: 
                answer.descriptive_answer = value
            answer.save()
            
        attempt.score = current_score
        attempt.save()
        if quiz.questions.filter(question_type='DESCRIPTIVE').exists():
            for faculty_profile in quiz.subject.faculty.all():
                Notification.objects.create(
                    recipient=faculty_profile.user,
                    message=f"'{student.user.get_full_name()}' has completed the quiz '{quiz.title}', which has questions awaiting your review."
                )

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
    
class FacultyDashboardView(LoginRequiredMixin, FacultyRequiredMixin, TemplateView):
    template_name = 'core/faculty_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faculty = self.request.user.faculty
        
        subjects = Subject.objects.filter(faculty=faculty).annotate(
            student_count=Count('course__students')
        ).order_by('title')
        
        ungraded_submissions = AssignmentSubmission.objects.filter(
            assignment__subject__faculty=faculty,
            grade__isnull=True
        ).order_by('-submitted_at')[:5] 
        
        now = timezone.now()
        next_week = now + timedelta(days=7)
        upcoming_assignments = Assignment.objects.filter(
            subject__faculty=faculty,
            due_date__gte=now,
            due_date__lte=next_week
        ).order_by('due_date')
        
        upcoming_quizzes = Quiz.objects.filter(
            subject__faculty=faculty,
            due_date__gte=now,
            due_date__lte=next_week
        ).order_by('due_date')
        
        context['subjects_with_stats'] = subjects
        context['ungraded_submissions'] = ungraded_submissions
        context['upcoming_assignments'] = upcoming_assignments
        context['upcoming_quizzes'] = upcoming_quizzes
        return context

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
        context = super().get_context_data(**kwargs)
        context['subject'] = Subject.objects.get(pk=self.kwargs['subject_pk'])
        return context

    def form_valid(self, form):
        subject = Subject.objects.get(pk=self.kwargs['subject_pk'])
        form.instance.subject = subject
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('core:faculty_subject_detail', kwargs={'pk': self.kwargs['subject_pk']})

# core/views.py

from .models import LearningResource # Ensure this is imported

# ...

class ResourceUpdateView(LoginRequiredMixin, FacultyRequiredMixin, UpdateView):
    model = LearningResource
    fields = ['title', 'description', 'file', 'link']
    template_name = 'core/resource_form.html' # We reuse the existing create form

    def get_queryset(self):
        # Security: Ensure faculty can only edit resources in subjects they teach
        return LearningResource.objects.filter(subject__faculty=self.request.user.faculty)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the subject to the template so the "Cancel" button works
        context['subject'] = self.object.subject
        return context
    
    def get_success_url(self):
        messages.success(self.request, "Resource updated successfully.")
        return reverse_lazy('core:faculty_subject_detail', kwargs={'pk': self.object.subject.pk})

class ResourceDeleteView(LoginRequiredMixin, FacultyRequiredMixin, DeleteView):
    model = LearningResource
    template_name = 'core/resource_confirm_delete.html'

    def get_queryset(self):
        # Security: Ensure faculty can only delete resources in subjects they teach
        return LearningResource.objects.filter(subject__faculty=self.request.user.faculty)

    def get_success_url(self):
        messages.success(self.request, "Resource deleted successfully.")
        return reverse_lazy('core:faculty_subject_detail', kwargs={'pk': self.object.subject.pk})

class AssignmentCreateView(LoginRequiredMixin, FacultyRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'core/assignment_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subject'] = Subject.objects.get(pk=self.kwargs['subject_pk'])
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        
        subject = Subject.objects.get(pk=self.kwargs['subject_pk'])
        self.object.subject = subject
        
        self.object.save()        
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
        messages.success(self.request, f"Grade for '{self.object.student.user.username}' has been saved.")
        submission = self.get_object()
        grade = form.cleaned_data.get('grade')
        Notification.objects.create(
            recipient=submission.student.user,
            message=f"Your submission for '{submission.assignment.title}' has been graded. You received {form.cleaned_data.get('grade')}."
        )
        messages.success(self.request, "Grade saved and student notified.")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle an invalid form submission by creating a clean error message."""
        error_list = []
        for field, errors in form.errors.items():
            for error in errors:
                error_list.append(error)
        clean_error_message = " ".join(error_list)
        messages.error(self.request, f"Failed to save grade. {clean_error_message}")
        submission = self.get_object()
        return redirect('core:view_submissions', pk=submission.assignment.pk)

class QuizCreateView(LoginRequiredMixin, FacultyRequiredMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'core/quiz_form.html'

    def form_valid(self, form):
        subject = Subject.objects.get(pk=self.kwargs['subject_pk'])
        form.instance.subject = subject
        self.object = form.save()

        course = self.object.subject.course
        students = course.students.all()
        for student_profile in students:
            Notification.objects.create(
                recipient=student_profile.user,
                message=f"A new quiz '{self.object.title}' has been posted for your course '{course.title}'."
            )
        
        messages.success(self.request, "Quiz created and students notified.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subject'] = Subject.objects.get(pk=self.kwargs['subject_pk'])
        return context

    def get_success_url(self):
        return reverse_lazy('core:quiz_detail', kwargs={'pk': self.object.pk})

class QuizDetailView(LoginRequiredMixin, FacultyRequiredMixin, DetailView):
    model = Quiz
    template_name = 'core/quiz_builder.html'
    context_object_name = 'quiz'

    def get_queryset(self):
        return Quiz.objects.filter(subject__faculty=self.request.user.faculty)


class QuizUpdateView(LoginRequiredMixin, FacultyRequiredMixin, UpdateView):
    model = Quiz
    form_class=QuizForm
    template_name = 'core/quiz_form.html'

    def get_queryset(self):
        return Quiz.objects.filter(subject__faculty=self.request.user.faculty)

    def get_success_url(self):
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
        
        quiz = Quiz.objects.get(pk=self.kwargs['quiz_pk'])
        form.instance.quiz = quiz
        self.object = form.save() 

        
        option_formset = MCQOptionFormSet(self.request.POST, instance=self.object)
        if option_formset.is_valid():
            option_formset.save()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('core:quiz_detail', kwargs={'pk': self.kwargs['quiz_pk']})

class QuizQuestionBulkUploadView(LoginRequiredMixin, FacultyRequiredMixin, View):
    template_name = 'core/quiz_bulk_upload.html'

    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, subject__faculty=request.user.faculty)
        form = FileUploadForm()
        return render(request, self.template_name, {'form': form, 'quiz': quiz})

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, subject__faculty=request.user.faculty)
        form = FileUploadForm(request.POST, request.FILES)

        if form.is_valid():
            csv_file = request.FILES['file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Error: This is not a CSV file.')
                return render(request, self.template_name, {'form': form, 'quiz': quiz})

            try:
                with transaction.atomic():
                    data_set = csv_file.read().decode('UTF-8')
                    io_string = io.StringIO(data_set)
                    next(io_string) # Skip header
                    
                    questions_created = 0
                    
                    # Expected CSV Format:
                    # Type, Question Text, Marks, Option1, Option2, Option3, Option4, Correct Option Index (1-4)
                    
                    for row_num, column in enumerate(csv.reader(io_string), 2):
                        # Basic cleanup
                        q_type = column[0].strip().upper() # MCQ or DESCRIPTIVE
                        q_text = column[1].strip()
                        q_marks = int(column[2].strip())
                        
                        if not q_text:
                            continue # Skip empty rows

                        # Create Question
                        question = Question.objects.create(
                            quiz=quiz,
                            text=q_text,
                            question_type=q_type,
                            marks=q_marks
                        )

                        # Handle Options for MCQ
                        if q_type == 'MCQ':
                            # Get options from columns 3, 4, 5, 6
                            options_text = [column[3].strip(), column[4].strip(), column[5].strip(), column[6].strip()]
                            
                            # Column 7 contains the index of the correct answer (1, 2, 3, or 4)
                            try:
                                correct_index = int(column[7].strip())
                            except ValueError:
                                raise Exception(f"Row {row_num}: Correct option index must be a number (1-4).")

                            if correct_index < 1 or correct_index > 4:
                                raise Exception(f"Row {row_num}: Correct option index must be between 1 and 4.")

                            for i, text in enumerate(options_text):
                                if text: # Only create option if text exists
                                    MCQOption.objects.create(
                                        question=question,
                                        text=text,
                                        is_correct=(i + 1 == correct_index)
                                    )
                        
                        questions_created += 1

                messages.success(request, f'Successfully uploaded {questions_created} questions.')
                return redirect('core:quiz_detail', pk=quiz.pk)

            except Exception as e:
                messages.error(request, f"Upload failed: {e}")

        return render(request, self.template_name, {'form': form, 'quiz': quiz})

class QuizAttemptsListView(LoginRequiredMixin, FacultyRequiredMixin, DetailView):
    model = Quiz
    template_name = 'core/quiz_attempts_list.html'
    context_object_name = 'quiz'

    def get_queryset(self):
        """Security: Faculty can only view attempts for quizzes in their subjects."""
        return Quiz.objects.filter(subject__faculty=self.request.user.faculty)



class GradeQuizAttemptView(LoginRequiredMixin, FacultyRequiredMixin, View):
    
    def get(self, request, pk):
        attempt = get_object_or_404(QuizAttempt, pk=pk, quiz__subject__faculty=request.user.faculty)
        DescriptiveAnswerFormSet = modelformset_factory(StudentAnswer, fields=('marks_awarded',), extra=0)
        descriptive_answers_qs = attempt.answers.filter(question__question_type='DESCRIPTIVE')
        formset = DescriptiveAnswerFormSet(queryset=descriptive_answers_qs)

        
        
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
        
        attempt = get_object_or_404(QuizAttempt, pk=pk, quiz__subject__faculty=request.user.faculty)
        DescriptiveAnswerFormSet = modelformset_factory(StudentAnswer, fields=('marks_awarded',), extra=0)
        descriptive_answers_qs = attempt.answers.filter(question__question_type='DESCRIPTIVE')
        formset = DescriptiveAnswerFormSet(request.POST, queryset=descriptive_answers_qs)
        
        if formset.is_valid():
            formset.save()
            
            total_score = attempt.answers.filter(mcq_option__is_correct=True).aggregate(
                total=models.Sum('question__marks')
            )['total'] or 0
            
            
            descriptive_score = 0
            for form in formset.cleaned_data:
                 if form.get('marks_awarded'):
                    descriptive_score += form['marks_awarded']

            attempt.score = total_score + descriptive_score
            attempt.save()
            Notification.objects.create(
                recipient=attempt.student.user,
                message=f"Your quiz '{attempt.quiz.title}' has been fully graded. Your final score is {attempt.score}."
            )
            messages.success(request, f"Successfully graded quiz for {attempt.student.user.get_full_name()}.")
            
            return redirect('core:quiz_attempts_list', pk=attempt.quiz.pk)
        
        
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
        
        queryset = super().get_queryset().filter(recipient=self.request.user)
        
        queryset.filter(is_read=False).update(is_read=True)
        return queryset