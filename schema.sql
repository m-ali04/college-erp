    -- =============================================
    -- College ERP — Learning Management System
    -- PostgreSQL Database Schema (3NF)
    -- =============================================

    -- Drop existing tables in reverse dependency order
    DROP TABLE IF EXISTS announcements CASCADE;
    DROP TABLE IF EXISTS student_fees CASCADE;
    DROP TABLE IF EXISTS marks CASCADE;
    DROP TABLE IF EXISTS attendance CASCADE;
    DROP TABLE IF EXISTS course_assignments CASCADE;
    DROP TABLE IF EXISTS enrollments CASCADE;
    DROP TABLE IF EXISTS courses CASCADE;
    DROP TABLE IF EXISTS teachers CASCADE;
    DROP TABLE IF EXISTS students CASCADE;
    DROP TABLE IF EXISTS users CASCADE;

    -- =============================================
    -- Table 1: users
    -- =============================================
    CREATE TABLE users (
        user_id      SERIAL PRIMARY KEY,
        full_name    VARCHAR(100) NOT NULL,
        email        VARCHAR(150) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        role         VARCHAR(20) CHECK (role IN ('student', 'teacher', 'admin')) NOT NULL,
        created_at   TIMESTAMP DEFAULT NOW()
    );

    -- =============================================
    -- Table 2: students
    -- =============================================
    CREATE TABLE students (
        student_id  SERIAL PRIMARY KEY,
        user_id     INT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
        roll_no     VARCHAR(20) UNIQUE,
        department  VARCHAR(100),
        batch_year  INT,
        section     VARCHAR(10)
    );

    -- =============================================
    -- Table 3: teachers
    -- =============================================
    CREATE TABLE teachers (
        teacher_id    SERIAL PRIMARY KEY,
        user_id       INT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
        employee_code VARCHAR(30) UNIQUE,
        department    VARCHAR(100),
        designation   VARCHAR(100)
    );

    -- =============================================
    -- Table 4: courses
    -- =============================================
    CREATE TABLE courses (
        course_id    SERIAL PRIMARY KEY,
        course_code  VARCHAR(20) UNIQUE,
        course_name  VARCHAR(150),
        credit_hours INT CHECK (credit_hours > 0),
        department   VARCHAR(100)
    );

    -- =============================================
    -- Table 5: enrollments
    -- =============================================
    CREATE TABLE enrollments (
        enrollment_id SERIAL PRIMARY KEY,
        student_id    INT NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
        course_id     INT NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT,
        semester      VARCHAR(20),
        academic_year VARCHAR(10)
    );

    -- =============================================
    -- Table 6: course_assignments
    -- =============================================
    CREATE TABLE course_assignments (
        assignment_id SERIAL PRIMARY KEY,
        teacher_id    INT NOT NULL REFERENCES teachers(teacher_id) ON DELETE RESTRICT,
        course_id     INT NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT,
        semester      VARCHAR(20),
        academic_year VARCHAR(10)
    );

    -- =============================================
    -- Table 7: attendance
    -- =============================================
    CREATE TABLE attendance (
        attendance_id SERIAL PRIMARY KEY,
        enrollment_id INT NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE RESTRICT,
        date          DATE NOT NULL,
        status        VARCHAR(10) CHECK (status IN ('present', 'absent', 'late')) NOT NULL,
        UNIQUE(enrollment_id, date)
    );

    -- =============================================
    -- Table 8: marks
    -- =============================================
    CREATE TABLE marks (
        mark_id        SERIAL PRIMARY KEY,
        enrollment_id  INT NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE RESTRICT,
        exam_type      VARCHAR(20) CHECK (exam_type IN ('midterm', 'final', 'quiz', 'assignment')) NOT NULL,
        obtained_marks NUMERIC(5,2) CHECK (obtained_marks >= 0),
        total_marks    NUMERIC(5,2) CHECK (total_marks > 0),
        remarks        TEXT
    );

    -- =============================================
    -- Table 9: announcements
    -- =============================================
    CREATE TABLE announcements (
        announcement_id SERIAL PRIMARY KEY,
        posted_by       INT REFERENCES users(user_id),
        course_id       INT REFERENCES courses(course_id),
        title           VARCHAR(200),
        body            TEXT,
        created_at      TIMESTAMP DEFAULT NOW()
    );

    -- =============================================
    -- Performance Indexes
    -- =============================================
    CREATE INDEX idx_students_user_id ON students(user_id);
    CREATE INDEX idx_teachers_user_id ON teachers(user_id);
    CREATE INDEX idx_enrollments_student_id ON enrollments(student_id);
    CREATE INDEX idx_enrollments_course_id ON enrollments(course_id);
    CREATE INDEX idx_course_assignments_teacher_id ON course_assignments(teacher_id);
    CREATE INDEX idx_course_assignments_course_id ON course_assignments(course_id);
    CREATE INDEX idx_attendance_enrollment_id ON attendance(enrollment_id);
    CREATE INDEX idx_attendance_date ON attendance(date);
    CREATE INDEX idx_marks_enrollment_id ON marks(enrollment_id);
    CREATE INDEX idx_announcements_course_id ON announcements(course_id);
    CREATE INDEX idx_announcements_posted_by ON announcements(posted_by);

    -- =============================================
    -- Table 10: student_fees
    -- =============================================
    CREATE TABLE student_fees (
        fee_id SERIAL PRIMARY KEY,
        student_id INT NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
        fee_type VARCHAR(50) NOT NULL,
        amount NUMERIC(10,2) CHECK (amount > 0) NOT NULL,
        due_date DATE NOT NULL,
        status VARCHAR(20) CHECK (status IN ('pending', 'paid', 'overdue')) DEFAULT 'pending' NOT NULL,
        payment_date DATE,
        created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE INDEX idx_student_fees_student_id ON student_fees(student_id);
