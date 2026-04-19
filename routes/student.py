"""Student blueprint — read-only views for courses, attendance, marks, announcements."""
from flask import Blueprint, render_template, session, flash, redirect, url_for, request
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

    # Marks aggregated by exam type
    marks_by_type = execute_query("""
        SELECT m.exam_type,
               SUM(m.obtained_marks) AS obtained,
               SUM(m.total_marks)    AS total
        FROM marks m
        JOIN enrollments e ON m.enrollment_id = e.enrollment_id
        WHERE e.student_id = %s
        GROUP BY m.exam_type
        ORDER BY m.exam_type
    """, (sid,), fetch=True)

    # Per-course marks summary (latest/best per course)
    course_marks = execute_query("""
        SELECT c.course_code, c.course_name,
               SUM(m.obtained_marks) AS obtained,
               SUM(m.total_marks)    AS total
        FROM marks m
        JOIN enrollments e ON m.enrollment_id = e.enrollment_id
        JOIN courses c     ON e.course_id     = c.course_id
        WHERE e.student_id = %s
        GROUP BY c.course_code, c.course_name
        ORDER BY c.course_code
        LIMIT 8
    """, (sid,), fetch=True)

    # Fees summary
    execute_query(
        "UPDATE student_fees SET status='overdue' WHERE status='pending' AND due_date < CURRENT_DATE AND student_id=%s",
        (sid,)
    )
    fees_summary = execute_query("""
        SELECT
            COUNT(*) AS total_invoices,
            SUM(CASE WHEN status='paid'    THEN amount ELSE 0 END) AS paid,
            SUM(CASE WHEN status='pending' THEN amount ELSE 0 END) AS pending,
            SUM(CASE WHEN status='overdue' THEN amount ELSE 0 END) AS overdue,
            COUNT(CASE WHEN status='paid'    THEN 1 END) AS paid_count,
            COUNT(CASE WHEN status='pending' THEN 1 END) AS pending_count,
            COUNT(CASE WHEN status='overdue' THEN 1 END) AS overdue_count
        FROM student_fees WHERE student_id = %s
    """, (sid,), fetchone=True)

    # Recent 5 fees invoices
    recent_fees = execute_query("""
        SELECT fee_type, amount, status, due_date
        FROM student_fees WHERE student_id = %s
        ORDER BY created_at DESC LIMIT 5
    """, (sid,), fetch=True)

    return render_template('student/dashboard.html',
                           student=student, course_count=course_count,
                           attendance=att, announcements=announcements,
                           marks_by_type=marks_by_type,
                           course_marks=course_marks,
                           fees_summary=fees_summary,
                           recent_fees=recent_fees)


@student_bp.route('/courses')
@role_required('student')
def courses():
    sid = _student_id()
    if not sid:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    where_clause = ""
    params = [sid]
    
    if search_query:
        where_clause = "AND (c.course_code ILIKE %s OR c.course_name ILIKE %s)"
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q])
        
    query = f"""
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
        WHERE e.student_id = %s {where_clause}
        ORDER BY e.enrollment_id, e.academic_year DESC, e.semester
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    rows = execute_query(query, tuple(params), fetch=True)

    if is_ajax:
        html = render_template('student/partials/course_rows.html', courses=rows)
        return {"html": html, "count": len(rows)}

    return render_template('student/courses.html', courses=[])


@student_bp.route('/attendance')
@role_required('student')
def attendance():
    sid = _student_id()
    if not sid:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    where_clause = ""
    params = [sid]
    
    if search_query:
        where_clause = "AND (c.course_code ILIKE %s OR c.course_name ILIKE %s)"
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q])
        
    query = f"""
        SELECT e.enrollment_id, c.course_code, c.course_name,
               COUNT(CASE WHEN a.status='present' THEN 1 END) AS present_count,
               COUNT(CASE WHEN a.status='late'    THEN 1 END) AS late_count,
               COUNT(CASE WHEN a.status='absent'  THEN 1 END) AS absent_count,
               COUNT(a.attendance_id)                          AS total_classes
        FROM enrollments e
        JOIN courses c ON e.course_id = c.course_id
        LEFT JOIN attendance a ON e.enrollment_id = a.enrollment_id
        WHERE e.student_id = %s {where_clause}
        GROUP BY e.enrollment_id, c.course_code, c.course_name
        ORDER BY c.course_code
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    data = execute_query(query, tuple(params), fetch=True)

    if is_ajax:
        html = render_template('student/partials/attendance_rows.html', attendance_data=data)
        return {"html": html, "count": len(data)}

    return render_template('student/attendance.html', attendance_data=[])


@student_bp.route('/marks')
@role_required('student')
def marks():
    sid = _student_id()
    if not sid:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    is_ajax    = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    exam_type  = request.args.get('exam_type', '').strip().lower()
    offset     = int(request.args.get('offset', 0))
    limit      = int(request.args.get('limit', 20))

    conditions = []
    params     = [sid]

    if search_query:
        conditions.append("(c.course_code ILIKE %s OR c.course_name ILIKE %s)")
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q])

    # Map friendly tab names → DB values (partial match so "midterm" matches "mid", "finals" matches "final" etc.)
    EXAM_TYPE_MAP = {
        'quiz':       'quiz',
        'assignment': 'assignment',
        'midterm':    'mid',
        'final':      'final',
    }
    if exam_type and exam_type in EXAM_TYPE_MAP:
        conditions.append("m.exam_type ILIKE %s")
        params.append(f"%{EXAM_TYPE_MAP[exam_type]}%")

    where_extra = ("AND " + " AND ".join(conditions)) if conditions else ""

    query = f"""
        SELECT c.course_code, c.course_name,
               m.exam_type, m.obtained_marks, m.total_marks, m.remarks
        FROM marks m
        JOIN enrollments e ON m.enrollment_id = e.enrollment_id
        JOIN courses c     ON e.course_id     = c.course_id
        WHERE e.student_id = %s {where_extra}
        ORDER BY c.course_code, m.exam_type
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    data = execute_query(query, tuple(params), fetch=True)

    if is_ajax:
        html = render_template('student/partials/marks_rows.html', marks_data=data)
        return {"html": html, "count": len(data)}

    # Summary stats per exam type for the header badges
    summary = execute_query("""
        SELECT m.exam_type,
               SUM(m.obtained_marks) AS obtained,
               SUM(m.total_marks)    AS total,
               COUNT(*)              AS cnt
        FROM marks m
        JOIN enrollments e ON m.enrollment_id = e.enrollment_id
        WHERE e.student_id = %s
        GROUP BY m.exam_type
        ORDER BY m.exam_type
    """, (sid,), fetch=True)

    return render_template('student/marks.html', marks_data=[], marks_summary=summary)


@student_bp.route('/announcements')
@role_required('student')
def announcements():
    sid = _student_id()
    if not sid:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))

    where_clause = ""
    params = [sid]

    if search_query:
        where_clause = "AND (a.title ILIKE %s OR a.body ILIKE %s)"
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q])

    query = f"""
        SELECT a.*, u.full_name AS poster_name, c.course_name, c.course_code
        FROM announcements a
        JOIN users u ON a.posted_by = u.user_id
        LEFT JOIN courses c ON a.course_id = c.course_id
        WHERE (a.course_id IS NULL
           OR a.course_id IN (SELECT e.course_id FROM enrollments e WHERE e.student_id = %s))
        {where_clause}
        ORDER BY a.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    rows = execute_query(query, tuple(params), fetch=True)

    if is_ajax:
        html = render_template('student/partials/announcement_rows.html', announcements=rows)
        return {"html": html, "count": len(rows)}

    return render_template('student/announcements.html', announcements=[])


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

    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))

    where_clause = ""
    params = [sid]

    if search_query:
        where_clause = "AND fee_type ILIKE %s"
        like_q = f"%{search_query}%"
        params.append(like_q)

    query = f"""
        SELECT * FROM student_fees
        WHERE student_id = %s {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    fees_data = execute_query(query, tuple(params), fetch=True)

    if is_ajax:
        html = render_template('student/partials/fee_rows.html', fees=fees_data)
        return {"html": html, "count": len(fees_data)}

    # Compute totals for the summary cards (uses all records, not paginated)
    all_fees = execute_query(
        "SELECT amount, status FROM student_fees WHERE student_id = %s", (sid,), fetch=True
    )
    total_outstanding = sum(f['amount'] for f in all_fees if f['status'] in ('pending', 'overdue'))
    total_paid = sum(f['amount'] for f in all_fees if f['status'] == 'paid')

    return render_template('student/fees.html', fees=[], total_outstanding=total_outstanding, total_paid=total_paid)

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
