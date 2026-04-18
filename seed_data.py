import psycopg2
from config import Config

def seed_database():
    print("Connecting to PostgreSQL to seed data...")
    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )

    try:
        with conn.cursor() as cur:
            # 1. Add Teacher
            print("Seeding Teacher...")
            teacher_pass = 'teacher123'
            cur.execute(
                """INSERT INTO users (full_name, email, password, role)
                   VALUES (%s, %s, %s, %s) RETURNING user_id""",
                ('John Teacher', 'teacher@college.edu', teacher_pass, 'teacher')
            )
            teacher_user_id = cur.fetchone()[0]

            cur.execute(
                """INSERT INTO teachers (user_id, employee_code, department, designation)
                   VALUES (%s, %s, %s, %s) RETURNING teacher_id""",
                (teacher_user_id, 'EMP-001', 'Computer Science', 'Professor')
            )
            teacher_id = cur.fetchone()[0]

            # 2. Add Student
            print("Seeding Student...")
            student_pass = 'student123'
            cur.execute(
                """INSERT INTO users (full_name, email, password, role)
                   VALUES (%s, %s, %s, %s) RETURNING user_id""",
                ('Alice Student', 'student@college.edu', student_pass, 'student')
            )
            student_user_id = cur.fetchone()[0]

            cur.execute(
                """INSERT INTO students (user_id, roll_no, department, batch_year, section)
                   VALUES (%s, %s, %s, %s, %s) RETURNING student_id""",
                (student_user_id, 'CS-2023-01', 'Computer Science', 2023, 'A')
            )
            student_id = cur.fetchone()[0]

            # 3. Add Course
            print("Seeding Course...")
            cur.execute(
                """INSERT INTO courses (course_code, course_name, credit_hours, department)
                   VALUES (%s, %s, %s, %s) RETURNING course_id""",
                ('CS101', 'Introduction to Programming', 3, 'Computer Science')
            )
            course_id = cur.fetchone()[0]

            # 4. Enroll Student in Course
            print("Enrolling Student...")
            cur.execute(
                """INSERT INTO enrollments (student_id, course_id, semester, academic_year)
                   VALUES (%s, %s, %s, %s) RETURNING enrollment_id""",
                (student_id, course_id, 'Fall', '2023-2024')
            )
            enrollment_id = cur.fetchone()[0]

            # 5. Assign Course to Teacher
            print("Assigning Course to Teacher...")
            cur.execute(
                """INSERT INTO course_assignments (teacher_id, course_id, semester, academic_year)
                   VALUES (%s, %s, %s, %s)""",
                (teacher_id, course_id, 'Fall', '2023-2024')
            )

            # 6. Add some marks and attendance
            cur.execute(
                """INSERT INTO attendance (enrollment_id, date, status)
                   VALUES (%s, CURRENT_DATE, %s)""",
                (enrollment_id, 'present')
            )
            
            cur.execute(
                """INSERT INTO marks (enrollment_id, exam_type, obtained_marks, total_marks, remarks)
                   VALUES (%s, %s, %s, %s, %s)""",
                (enrollment_id, 'midterm', 85, 100, 'Good')
            )

            conn.commit()
            print("\nDatabase seeded successfully!")
            print("=" * 50)
            print("Teacher Login:")
            print("Email:    teacher@college.edu")
            print("Password: teacher123")
            print("=" * 50)
            print("Student Login:")
            print("Email:    student@college.edu")
            print("Password: student123")
            print("=" * 50)

    except Exception as e:
        conn.rollback()
        print(f"\nError seeding database: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    seed_database()
