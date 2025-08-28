# dashboard/views.py
from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from enrollment.models import Enrollment
from academics.models import Course, Content,Module
from academics.forms import ModuleForm, ContentForm # Import ContentForm
from collections import defaultdict

@login_required
def dashboard_view(request):
    user = request.user
    context = {}

    # --- Student Dashboard Logic ---
    if user.role == 'STUDENT':
        try:
            # Get the student's enrollment details
            enrollment = Enrollment.objects.get(student=user)
            program = enrollment.program
            
            # Get all courses for that program
            courses_qs = Course.objects.filter(program=program).order_by('semester', 'title')
            
            # Group courses by semester for easier display in the template
            courses_by_semester = defaultdict(list)
            for course in courses_qs:
                courses_by_semester[course.semester].append(course)
            
            context = {
                'enrollment': enrollment,
                'program': program,
                'courses_by_semester': dict(courses_by_semester),
            }
            return render(request, 'dashboard/student_dashboard.html', context)
        except Enrollment.DoesNotExist:
            # Handle case where a student user is not yet enrolled in any program
            context['message'] = "You are not yet enrolled in a program. Please contact an administrator."
            return render(request, 'dashboard/no_enrollment.html', context)

    # --- Add logic for other roles later ---
    elif user.role == 'FACULTY':
         # Fetch all courses taught by this faculty member
        courses_taught = Course.objects.filter(faculty=user).order_by('program', 'title')
        context = {
            'courses_taught': courses_taught,
        }
        return render(request, 'dashboard/faculty_dashboard.html', context)
    
    else: # For HOD, Admin, etc.
        context['message'] = "Welcome to the Edusphere dashboard."
        return render(request, 'dashboard/generic_dashboard.html', context)
    
@login_required
def course_detail_view(request, pk):
    """
    Displays the modules and content for a single course.
    """
    user = request.user
    course = get_object_or_404(Course, pk=pk)

    # Security Check: Ensure the user is a student enrolled in this course's program
    if user.role == 'STUDENT':
        try:
            enrollment = Enrollment.objects.get(student=user)
            if course.program != enrollment.program:
                # If the course's program doesn't match the student's enrolled program
                return HttpResponseForbidden("You are not authorized to view this course.")
        except Enrollment.DoesNotExist:
            return HttpResponseForbidden("You are not enrolled in any program.")

    # Fetch modules and prefetch related content to avoid extra database queries
    modules = course.modules.prefetch_related('contents').all()
    
    context = {
        'course': course,
        'modules': modules,
    }

    return render(request, 'dashboard/course_detail.html', context)


@login_required
def content_detail_view(request, pk):
    """
    Displays a single piece of content.
    """
    user = request.user
    content = get_object_or_404(Content, pk=pk)

    # Security Check: Traverse up from content -> module -> course -> program
    # to ensure the student is enrolled in the content's parent program.
    if user.role == 'STUDENT':
        try:
            enrollment = Enrollment.objects.get(student=user)
            # This checks if the student's program matches the content's program
            if content.module.course.program != enrollment.program:
                return HttpResponseForbidden("You are not authorized to view this content.")
        except Enrollment.DoesNotExist:
            return HttpResponseForbidden("You are not enrolled in any program.")

    context = {
        'content': content,
    }
    return render(request, 'dashboard/content_detail.html', context)

@login_required
def manage_course_view(request, pk):
    """
    Allows faculty to manage a course, including adding/editing modules and content.
    """
    course = get_object_or_404(Course, pk=pk)

    # Authorization Check: Ensure user is faculty and is assigned to this course.
    if not request.user.role == 'FACULTY' or course.faculty != request.user:
        return HttpResponseForbidden("You are not authorized to manage this course.")

    # Handle the form submission for adding a new module
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            new_module = form.save(commit=False)
            new_module.course = course
            # Set the order for the new module
            last_module = course.modules.order_by('-order').first()
            new_module.order = last_module.order + 1 if last_module else 1
            new_module.save()
            return redirect('manage_course', pk=course.pk) # Redirect to the same page
    else:
        form = ModuleForm() # An empty form for a GET request

    modules = course.modules.all()
    context = {
        'course': course,
        'modules': modules,
        'form': form,
    }
    return render(request, 'dashboard/manage_course.html', context)





@login_required
def manage_module_view(request, pk):
    """
    Allows faculty to manage a module's content.
    """
    module = get_object_or_404(Module, pk=pk)
    course = module.course

    # Authorization Check
    if not request.user.role == 'FACULTY' or course.faculty != request.user:
        return HttpResponseForbidden("You are not authorized to manage this module.")

    # Handle form submission for adding new content
    if request.method == 'POST':
        # Must include request.FILES for file uploads
        form = ContentForm(request.POST, request.FILES)
        if form.is_valid():
            new_content = form.save(commit=False)
            new_content.module = module
            # Set the order for the new content
            last_content = module.contents.order_by('-order').first()
            new_content.order = last_content.order + 1 if last_content else 1
            new_content.save()
            return redirect('manage_module', pk=module.pk)
    else:
        form = ContentForm()

    context = {
        'module': module,
        'form': form,
    }
    return render(request, 'dashboard/manage_module.html', context)

# dashboard/views.py
# ... other imports and views

@login_required
def edit_content_view(request, pk):
    """
    Handles editing an existing piece of content.
    """
    content = get_object_or_404(Content, pk=pk)
    module = content.module
    course = module.course

    # Authorization Check
    if not request.user.role == 'FACULTY' or course.faculty != request.user:
        return HttpResponseForbidden("You are not authorized to edit this content.")

    if request.method == 'POST':
        # Pass the 'instance' to update the existing object
        form = ContentForm(request.POST, request.FILES, instance=content)
        if form.is_valid():
            form.save()
            # Redirect back to the module management page
            return redirect('manage_module', pk=module.pk)
    else:
        # Pre-fill the form with the existing content's data
        form = ContentForm(instance=content)

    context = {
        'form': form,
        'content': content
    }
    return render(request, 'dashboard/edit_content.html', context)


@login_required
def delete_content_view(request, pk):
    """
    Handles deleting an existing piece of content after confirmation.
    """
    content = get_object_or_404(Content, pk=pk)
    module = content.module
    course = module.course

    # Authorization Check
    if not request.user.role == 'FACULTY' or course.faculty != request.user:
        return HttpResponseForbidden("You are not authorized to delete this content.")

    if request.method == 'POST':
        content.delete()
        return redirect('manage_module', pk=module.pk)

    context = {
        'content': content
    }
    return render(request, 'dashboard/delete_content_confirm.html', context)



@login_required
def edit_module_view(request, pk):
    """
    Handles editing an existing module.
    """
    module = get_object_or_404(Module, pk=pk)
    course = module.course

    # Authorization Check
    if not request.user.role == 'FACULTY' or course.faculty != request.user:
        return HttpResponseForbidden("You are not authorized to edit this module.")

    if request.method == 'POST':
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            return redirect('manage_course', pk=course.pk)
    else:
        form = ModuleForm(instance=module)

    context = {
        'form': form,
        'module': module
    }
    return render(request, 'dashboard/edit_module.html', context)


@login_required
def delete_module_view(request, pk):
    """
    Handles deleting an existing module and its content after confirmation.
    """
    module = get_object_or_404(Module, pk=pk)
    course = module.course

    # Authorization Check
    if not request.user.role == 'FACULTY' or course.faculty != request.user:
        return HttpResponseForbidden("You are not authorized to delete this module.")

    if request.method == 'POST':
        module.delete()
        return redirect('manage_course', pk=course.pk)

    context = {
        'module': module
    }
    return render(request, 'dashboard/delete_module_confirm.html', context)