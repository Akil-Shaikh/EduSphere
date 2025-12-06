# core/management/commands/populate_data.py

import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from faker import Faker
from core.models import (
    University, Department, Course, Subject, Faculty, Student, 
    UniversityAdmin, Enrollment
)

class Command(BaseCommand):
    help = 'Populates the database with a large set of realistic sample data for EduSphere'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "\nThis command will DELETE ALL existing data (except superusers) and repopulate the database."
        ))
        confirm = input("Are you sure you want to continue? (yes/no): ")
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.ERROR("Operation cancelled."))
            return

        self.stdout.write("Deleting old data...")
        models_to_clear = [University, Department, Course, Subject, Faculty, Student, UniversityAdmin, Enrollment]
        for m in models_to_clear:
            m.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        self.stdout.write("Creating new data...")
        fake = Faker()

        university_data = [
            ("Gujarat Technological University", "GTU"),
            ("Nirma University", "NU"),
        ]
        
        department_names = ["Computer Science", "Mechanical Engineering", "Electrical Engineering", "Civil Engineering"]

        for uni_name, uni_abbr in university_data:
            self.stdout.write(self.style.SUCCESS(f"\n--- Populating {uni_name} ---"))

            university = University.objects.create(name=uni_name)
            
            admin_username_str = f'admin_{uni_abbr.lower()}'
            admin_user = User.objects.create_user(
                username=admin_username_str, password='password123', 
                first_name=uni_abbr, last_name='Admin'
            )
            UniversityAdmin.objects.create(user=admin_user, university=university)
            self.stdout.write(f"Created University Admin: {admin_user.username}")

            uni_departments = [Department.objects.create(name=name, university=university) for name in department_names]
            self.stdout.write(f"Created {len(uni_departments)} departments.")

            uni_faculties = []
            for i in range(8):
                first_name = fake.first_name()
                last_name = fake.last_name()
                faculty_user = User.objects.create_user(
                    username=f'prof_{uni_abbr.lower()}_{first_name.lower()}{i}',
                    password='password123',
                    first_name=first_name,
                    last_name=last_name
                )
                faculty = Faculty.objects.create(
                    user=faculty_user, university=university,
                    department=random.choice(uni_departments),
                    employee_id=f'{uni_abbr}-FAC-{str(i+1).zfill(3)}'
                )
                uni_faculties.append(faculty)
            self.stdout.write(f"Created {len(uni_faculties)} faculty members.")
            
            # --- CORRECTED LOGIC FOR HOD and FACULTY ASSIGNMENT ---
            
            # 1. Create a mutable copy of the faculty list to select HODs from.
            faculty_pool = list(uni_faculties)
            
            # 2. Assign HODs and remove them from the pool of available teachers.
            for dept in uni_departments:
                hod_candidate = random.choice(faculty_pool)
                dept.hod = hod_candidate
                dept.save()
                faculty_pool.remove(hod_candidate) # This HOD is no longer available for teaching roles
            
            # 3. The remaining faculty in 'faculty_pool' are the non-HOD teachers.
            non_hod_faculty = faculty_pool
            self.stdout.write(f"Assigned HODs and created a pool of {len(non_hod_faculty)} non-HOD teaching faculty.")
            
            student_id_counter = 1
            for dept in uni_departments:
                self.stdout.write(f"  - Populating Department: {dept.name}")
                for i in range(2): 
                    course = Course.objects.create(
                        title=f"{dept.name} Course {i+1}",
                        code=f"{uni_abbr}-{dept.name[:3].upper()}-C{i+1}",
                        department=dept,
                        university=university
                    )
                    self.stdout.write(f"    - Created Course: {course.code}")

                    for j in range(6):
                        subject = Subject.objects.create(
                            title=f"Subject {j+1} for {course.code}",
                            code=f"{course.code}-S{j+1}",
                            course=course
                        )
                        # 4. Assign 2 faculty members from the NON-HOD pool only.
                        assigned_faculty = random.sample(non_hod_faculty, 2)
                        subject.faculty.set(assigned_faculty)

                    self.stdout.write(f"      - Enrolling 50 students...", ending="")
                    for k in range(50):
                        first_name = fake.first_name()
                        last_name = fake.last_name()
                        student_user = User.objects.create_user(
                            username=f'student_{uni_abbr.lower()}_{course.code}_{k+1}',
                            password='password123',
                            first_name=first_name,
                            last_name=last_name
                        )
                        student = Student.objects.create(
                            user=student_user,
                            university=university,
                            student_id=f'{uni_abbr}-ST-{str(student_id_counter).zfill(4)}'
                        )
                        student_id_counter += 1
                        
                        Enrollment.objects.create(
                            student=student,
                            course=course,
                            roll_number=f'{course.code}-{str(k+1).zfill(3)}'
                        )
                    self.stdout.write(self.style.SUCCESS(" Done."))

        self.stdout.write(self.style.SUCCESS("\nDatabase has been successfully populated with sample data!"))