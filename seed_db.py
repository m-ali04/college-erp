"""
Database Seeding Script.
Populates the database with comprehensive mock data for testing.
"""
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
from config import Config

def get_connection():
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )

def seed_database():
    print("Connecting to PostgreSQL to seed mock data...")
    conn = get_connection()
    password = 'password123'
    
    try:
        with conn.cursor() as cur:
            print("Cleaning existing data (except admin)...")
            cur.execute("TRUNCATE student_fees, announcements, marks, attendance, enrollments, course_assignments, courses, students, teachers CASCADE")
            cur.execute("DELETE FROM users WHERE role IN ('teacher', 'student')")
            
            # ----------------------------------------------------
            # 1. Teachers
            # ----------------------------------------------------
            print("Seeding teachers...")
            teachers_data = [
                ('Alice Alan', 'alice@college.edu', 'password123', 'teacher', 'EMP-001', 'Computer Science'),
                ('Bob Boolean', 'bob@college.edu', 'password123', 'teacher', 'EMP-002', 'Mathematics'),
                ('Charlie Compiler', 'charlie@college.edu', 'password123', 'teacher', 'EMP-003', 'Physics')
            ]
            t_ids = {}
            for name, email, pwd, role, emp_code, dept in teachers_data:
                cur.execute("INSERT INTO users (full_name, email, password, role) VALUES (%s, %s, %s, %s) RETURNING user_id", (name, email, pwd, role))
                u_id = cur.fetchone()[0]
                cur.execute("INSERT INTO teachers (user_id, employee_code, department) VALUES (%s, %s, %s) RETURNING teacher_id", (u_id, emp_code, dept))
                t_ids[name] = cur.fetchone()[0]
                
            # ----------------------------------------------------
            # 2. Students
            # ----------------------------------------------------
            print("Seeding students...")
            students_data = [
                ('David Data', 'david@college.edu', 'STU-1001', 'Computer Science', 2026, 'A'),
                ('Ella Engine', 'ella@college.edu', 'STU-1002', 'Computer Science', 2026, 'B'),
                ('Frank Function', 'frank@college.edu', 'STU-1003', 'Mathematics', 2026, 'A'),
                ('Grace Graph', 'grace@college.edu', 'STU-1004', 'Computer Science', 2026, 'A'),
                ('Hugo Hash', 'hugo@college.edu', 'STU-1005', 'Physics', 2026, 'A')
            ]
            s_ids = {}
            for name, email, roll, dept, batch, sec in students_data:
                cur.execute("INSERT INTO users (full_name, email, password, role) VALUES (%s, %s, %s, 'student') RETURNING user_id", (name, email, password))
                u_id = cur.fetchone()[0]
                cur.execute("INSERT INTO students (user_id, roll_no, department, batch_year, section) VALUES (%s, %s, %s, %s, %s) RETURNING student_id", (u_id, roll, dept, batch, sec))
                s_ids[name] = cur.fetchone()[0]
                
            # ----------------------------------------------------
            # 3. Courses
            # ----------------------------------------------------
            print("Seeding courses...")
            courses_data = [
                ('CS101', 'Intro to Programming', 4, 'Computer Science'),
                ('CS202', 'Data Structures', 4, 'Computer Science'),
                ('MA101', 'Calculus I', 3, 'Mathematics'),
                ('PH101', 'Physics I', 3, 'Physics')
            ]
            c_ids = {}
            for code, name, cr, dept in courses_data:
                cur.execute("INSERT INTO courses (course_code, course_name, credit_hours, department) VALUES (%s, %s, %s, %s) RETURNING course_id", (code, name, cr, dept))
                c_ids[code] = cur.fetchone()[0]
                
            # ----------------------------------------------------
            # 4. Assignments
            # ----------------------------------------------------
            print("Assigning teachers to courses...")
            cur.execute("INSERT INTO course_assignments (course_id, teacher_id, semester, academic_year) VALUES (%s, %s, %s, %s), (%s, %s, %s, %s), (%s, %s, %s, %s), (%s, %s, %s, %s)", (
                c_ids['CS101'], t_ids['Alice Alan'], 'Fall', '2026',
                c_ids['CS202'], t_ids['Alice Alan'], 'Fall', '2026',
                c_ids['MA101'], t_ids['Bob Boolean'], 'Fall', '2026',
                c_ids['PH101'], t_ids['Charlie Compiler'], 'Fall', '2026'
            ))

            # ----------------------------------------------------
            # 5. Enrollments
            # ----------------------------------------------------
            print("Enrolling students...")
            e_ids = {}
            enrollment_records = [
                (s_ids['David Data'], c_ids['CS101']), (s_ids['David Data'], c_ids['CS202']), (s_ids['David Data'], c_ids['MA101']),
                (s_ids['Ella Engine'], c_ids['CS101']), (s_ids['Ella Engine'], c_ids['MA101']),
                (s_ids['Frank Function'], c_ids['MA101']), (s_ids['Frank Function'], c_ids['PH101']),
                (s_ids['Grace Graph'], c_ids['CS202']), (s_ids['Grace Graph'], c_ids['PH101']),
                (s_ids['Hugo Hash'], c_ids['CS101']), (s_ids['Hugo Hash'], c_ids['PH101'])
            ]
            for s, c in enrollment_records:
                cur.execute("INSERT INTO enrollments (student_id, course_id, semester, academic_year) VALUES (%s, %s, 'Fall', '2026') RETURNING enrollment_id", (s, c))
                e_ids[(s, c)] = cur.fetchone()[0]

            # ----------------------------------------------------
            # 6. Attendance & Marks
            # ----------------------------------------------------
            print("Seeding attendance and marks...")
            today = datetime.now().date()
            for s, c in e_ids.keys():
                eid = e_ids[(s, c)]
                # Attendance
                cur.execute("INSERT INTO attendance (enrollment_id, date, status) VALUES (%s, %s, %s)", (eid, today - timedelta(days=2), 'present'))
                cur.execute("INSERT INTO attendance (enrollment_id, date, status) VALUES (%s, %s, %s)", (eid, today - timedelta(days=1), 'late'))
                cur.execute("INSERT INTO attendance (enrollment_id, date, status) VALUES (%s, %s, %s)", (eid, today, 'absent'))
                
                # Marks
                cur.execute("INSERT INTO marks (enrollment_id, exam_type, obtained_marks, total_marks) VALUES (%s, 'midterm', 85, 100)", (eid,))
                cur.execute("INSERT INTO marks (enrollment_id, exam_type, obtained_marks, total_marks) VALUES (%s, 'final', 92, 100)", (eid,))

            # ----------------------------------------------------
            # 7. Announcements
            # ----------------------------------------------------
            print("Seeding announcements...")
            cur.execute("INSERT INTO announcements (title, body, posted_by) VALUES (%s, %s, (SELECT user_id FROM users WHERE role='admin' LIMIT 1))", 
                        ("Welcome to Fall 2026!", "Have a great semester everyone. Midterms start next month."))
            cur.execute("INSERT INTO announcements (course_id, title, body, posted_by) VALUES (%s, %s, %s, (SELECT user_id FROM users WHERE email='alice@college.edu'))", 
                        (c_ids['CS101'], "CS101 Syllabus Released", "Please check your portal for the class syllabus and reading list."))

            # ----------------------------------------------------
            # 8. Student Fees
            # ----------------------------------------------------
            print("Seeding fees...")
            cur.execute("INSERT INTO student_fees (student_id, fee_type, amount, due_date, status) VALUES (%s, 'Tuition Fee', 2500.00, %s, 'pending')", (s_ids['David Data'], today + timedelta(days=15)))
            cur.execute("INSERT INTO student_fees (student_id, fee_type, amount, due_date, status) VALUES (%s, 'Library Fee', 150.00, %s, 'overdue')", (s_ids['David Data'], today - timedelta(days=5)))
            cur.execute("INSERT INTO student_fees (student_id, fee_type, amount, due_date, status, payment_date) VALUES (%s, 'Tuition Fee', 2500.00, %s, 'paid', %s)", (s_ids['Ella Engine'], today + timedelta(days=15), today - timedelta(days=1)))
            cur.execute("INSERT INTO student_fees (student_id, fee_type, amount, due_date, status) VALUES (%s, 'Tuition Fee', 2500.00, %s, 'pending')", (s_ids['Frank Function'], today + timedelta(days=15)))

            conn.commit()
            print("\nDatabase seeded successfully!")
            print("All dummy users (students and teachers) have the password: password123")
            
    except Exception as e:
        conn.rollback()
        print(f"\nError seeding database: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    seed_database()
