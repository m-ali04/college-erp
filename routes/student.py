"""Student blueprint — read-only views for courses, attendance, marks, announcements."""
from flask import Blueprint, render_template, session, flash, redirect, url_for
from routes.auth import role_required
from models.db import execute_query

student_bp = Blueprint('student', __name__)


def _student_id():
    row = execute_query(
        "SELECT student_id FROM students WHERE user_id = %s",
        (session['user_id'],), fetchone=True)
    return row['student_id'] if row else None


@student_bp.route('/dashboard')
@role_required('student')
def dashboard():
    sid = _student_id()
    if not sid:
        flash('Student profile not found. Contact admin.', 'danger')
        return redirect(url_for('auth.login'))

    student = execute_query("""
        SELECT s.*, u.full_name, u.email
        FROM students s JOIN users u ON s.user_id = u.user_id
        WHERE s.student_id = %s
    """, (sid,), fetchone=True)

    course_count = execute_query(
        "SELECT COUNT(*) AS c FROM enrollments WHERE student_id = %s",
        (sid,), fetchone=True)['c']

    att = execute_query("""
        SELECT
            COUNT(CASE WHEN a.status='present' THEN 1 END) AS present,
            COUNT(CASE WHEN a.status='absent'  THEN 1 END) AS absent,
            COUNT(CASE WHEN a.status='late'    THEN 1 END) AS late,
            COUNT(a.attendance_id) AS total
        FROM enrollments e
        LEFT JOIN attendance a ON e.enrollment_id = a.enrollment_id
        WHERE e.student_id = %s
    """, (sid,), fetchone=True)

    announcements = execute_query("""
        SELECT a.*, u.full_name AS poster_name, c.course_name, c.course_code
        FROM announcements a
        JOIN users u ON a.posted_by = u.user_id
        LEFT JOIN courses c ON a.course_id = c.course_id
        WHERE a.course_id IS NULL
           OR a.course_id IN (SELECT e.course_id FROM enrollments e WHERE e.student_id = %s)
        ORDER BY a.created_at DESC LIMIT 5
    """, (sid,), fetch=True)

    return render_template('student/dashboard.html',
                           student=student, course_count=course_count,
                           attendance=att, announcements=announcements)


@student_bp.route('/courses')
@role_required('student')
def courses():
    sid = _student_id()
    if not sid:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    rows = execute_query("""
        SELECT DISTINCT ON (e.enrollment_id)
               e.enrollment_id, e.semester, e.academic_year,
               c.course_code, c.course_name, c.credit_hours, c.department,
               u.full_name AS teacher_name
        FROM enrollments e
        JOIN courses c ON e.course_id = c.course_id
        LEFT JOIN course_assignments ca
               ON c.course_id = ca.course_id
              AND e.semester = ca.semester AND e.academic_year = ca.academic_year
        LEFT JOIN teachers t ON ca.teacher_id = t.teacher_id
        LEFT JOIN users u    ON t.user_id     = u.user_id
        WHERE e.student_id = %s
        ORDER BY e.enrollment_id, e.academic_year DESC, e.semester
    """, (sid,), fetch=True)

    return render_template('student/courses.html', courses=rows)


@student_bp.route('/attendance')
@role_required('student')
def attendance():
    sid = _student_id()
    if not sid:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    data = execute_query("""
        SELECT e.enrollment_id, c.course_code, c.course_name,
               COUNT(CASE WHEN a.status='present' THEN 1 END) AS present_count,
               COUNT(CASE WHEN a.status='late'    THEN 1 END) AS late_count,
               COUNT(CASE WHEN a.status='absent'  THEN 1 END) AS absent_count,
               COUNT(a.attendance_id)                          AS total_classes
        FROM enrollments e
        JOIN courses c ON e.course_id = c.course_id
        LEFT JOIN attendance a ON e.enrollment_id = a.enrollment_id
        WHERE e.student_id = %s
        GROUP BY e.enrollment_id, c.course_code, c.course_name
        ORDER BY c.course_code
    """, (sid,), fetch=True)

    return render_template('student/attendance.html', attendance_data=data)


@student_bp.route('/marks')
@role_required('student')
def marks():
    sid = _student_id()
    if not sid:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    data = execute_query("""
        SELECT c.course_code, c.course_name,
               m.exam_type, m.obtained_marks, m.total_marks, m.remarks
        FROM marks m
        JOIN enrollments e ON m.enrollment_id = e.enrollment_id
        JOIN courses c     ON e.course_id     = c.course_id
        WHERE e.student_id = %s
        ORDER BY c.course_code, m.exam_type
    """, (sid,), fetch=True)

    return render_template('student/marks.html', marks_data=data)


@student_bp.route('/announcements')
@role_required('student')
def announcements():
    sid = _student_id()
    if not sid:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    rows = execute_query("""
        SELECT a.*, u.full_name AS poster_name, c.course_name, c.course_code
        FROM announcements a
        JOIN users u ON a.posted_by = u.user_id
        LEFT JOIN courses c ON a.course_id = c.course_id
        WHERE a.course_id IS NULL
           OR a.course_id IN (SELECT e.course_id FROM enrollments e WHERE e.student_id = %s)
        ORDER BY a.created_at DESC
    """, (sid,), fetch=True)

    return render_template('student/announcements.html', announcements=rows)


# ================================================================== #
#  Fees
# ================================================================== #

@student_bp.route('/fees')
@role_required('student')
def fees():
    sid = _student_id()
    if not sid:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    execute_query("UPDATE student_fees SET status = 'overdue' WHERE status = 'pending' AND due_date < CURRENT_DATE AND student_id = %s", (sid,))

    fees_data = execute_query(
        "SELECT * FROM student_fees WHERE student_id = %s ORDER BY created_at DESC", 
        (sid,), fetch=True
    )
    
    total_outstanding = sum(f['amount'] for f in fees_data if f['status'] in ('pending', 'overdue'))
    total_paid = sum(f['amount'] for f in fees_data if f['status'] == 'paid')

    return render_template('student/fees.html', fees=fees_data, total_outstanding=total_outstanding, total_paid=total_paid)

@student_bp.route('/fees/<int:fee_id>/pay', methods=['POST'])
@role_required('student')
def simulate_payment(fee_id):
    sid = _student_id()
    try:
        execute_query(
            "UPDATE student_fees SET status = 'paid', payment_date = CURRENT_DATE WHERE fee_id = %s AND student_id = %s",
            (fee_id, sid)
        )
        flash('Simulated Payment Successful!', 'success')
    except Exception as e:
        flash(f'Error processing payment: {e}', 'danger')
    return redirect(url_for('student.fees'))
