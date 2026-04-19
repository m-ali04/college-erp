"""Teacher blueprint — attendance, marks entry, announcements."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import role_required
from models.db import execute_query

teacher_bp = Blueprint('teacher', __name__)


def _teacher_id():
    """Return the teacher_id for the logged-in user, or None."""
    row = execute_query(
        "SELECT teacher_id FROM teachers WHERE user_id = %s",
        (session['user_id'],), fetchone=True)
    return row['teacher_id'] if row else None


# ================================================================== #
#  Dashboard
# ================================================================== #

@teacher_bp.route('/dashboard')
@role_required('teacher')
def dashboard():
    tid = _teacher_id()
    if not tid:
        flash('Teacher profile not found. Contact admin.', 'danger')
        return redirect(url_for('auth.login'))

    courses = execute_query("""
        SELECT ca.*, c.course_code, c.course_name,
               c.credit_hours, c.department
        FROM course_assignments ca
        JOIN courses c ON ca.course_id = c.course_id
        WHERE ca.teacher_id = %s
        ORDER BY ca.academic_year DESC, ca.semester
    """, (tid,), fetch=True)

    for c in courses:
        c['student_count'] = execute_query(
            "SELECT COUNT(*) AS n FROM enrollments WHERE course_id = %s",
            (c['course_id'],), fetchone=True)['n']

    announcements = execute_query("""
        SELECT a.*, c.course_name, c.course_code
        FROM announcements a
        LEFT JOIN courses c ON a.course_id = c.course_id
        WHERE a.posted_by = %s
        ORDER BY a.created_at DESC LIMIT 5
    """, (session['user_id'],), fetch=True)

    return render_template('teacher/dashboard.html',
                           courses=courses, announcements=announcements)


# ================================================================== #
#  Attendance
# ================================================================== #

@teacher_bp.route('/attendance', methods=['GET', 'POST'])
@role_required('teacher')
def attendance():
    tid = _teacher_id()
    if not tid:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    # Courses assigned to this teacher
    courses = execute_query("""
        SELECT ca.assignment_id, ca.course_id, c.course_code, c.course_name
        FROM course_assignments ca
        JOIN courses c ON ca.course_id = c.course_id
        WHERE ca.teacher_id = %s
    """, (tid,), fetch=True)

    sel_course = request.args.get('course_id', '')
    sel_date   = request.args.get('date', '')
    students   = []

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        date      = request.form.get('date')

        if not course_id or not date:
            flash('Course and date are required.', 'danger')
            return redirect(url_for('teacher.attendance'))

        # Verify assignment
        ok = execute_query(
            "SELECT 1 FROM course_assignments WHERE teacher_id=%s AND course_id=%s",
            (tid, int(course_id)), fetchone=True)
        if not ok:
            flash('You are not assigned to this course.', 'danger')
            return redirect(url_for('teacher.attendance'))

        eids = request.form.getlist('enrollment_ids')
        for eid in eids:
            status = request.form.get(f'status_{eid}', '')
            if status in ('present', 'absent', 'late'):
                try:
                    execute_query("""
                        INSERT INTO attendance (enrollment_id, date, status)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (enrollment_id, date)
                        DO UPDATE SET status = EXCLUDED.status
                    """, (int(eid), date, status))
                except Exception as e:
                    flash(f'Error saving attendance: {e}', 'danger')
                    return redirect(url_for('teacher.attendance',
                                            course_id=course_id, date=date))

        flash('Attendance saved successfully.', 'success')
        return redirect(url_for('teacher.attendance',
                                course_id=course_id, date=date))

    # GET — load students when filters are set
    if sel_course and sel_date:
        students = execute_query("""
            SELECT e.enrollment_id, s.roll_no, u.full_name, s.section,
                   a.status AS existing_status
            FROM enrollments e
            JOIN students s ON e.student_id = s.student_id
            JOIN users u    ON s.user_id    = u.user_id
            LEFT JOIN attendance a
                   ON e.enrollment_id = a.enrollment_id AND a.date = %s
            WHERE e.course_id = %s
            ORDER BY s.roll_no
        """, (sel_date, int(sel_course)), fetch=True)

    return render_template('teacher/attendance.html',
                           courses=courses, students=students,
                           selected_course=sel_course, selected_date=sel_date)


# ================================================================== #
#  Marks Entry
# ================================================================== #

@teacher_bp.route('/marks', methods=['GET', 'POST'])
@role_required('teacher')
def marks():
    tid = _teacher_id()
    if not tid:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    courses = execute_query("""
        SELECT ca.assignment_id, ca.course_id, c.course_code, c.course_name
        FROM course_assignments ca
        JOIN courses c ON ca.course_id = c.course_id
        WHERE ca.teacher_id = %s
    """, (tid,), fetch=True)

    sel_course = request.args.get('course_id', '')
    sel_exam   = request.args.get('exam_type', '')
    students   = []

    if request.method == 'POST':
        course_id   = request.form.get('course_id')
        exam_type   = request.form.get('exam_type')
        total_marks = request.form.get('total_marks', '').strip()

        if not all([course_id, exam_type, total_marks]):
            flash('Course, exam type, and total marks are required.', 'danger')
            return redirect(url_for('teacher.marks'))

        if exam_type not in ('midterm', 'final', 'quiz', 'assignment'):
            flash('Invalid exam type.', 'danger')
            return redirect(url_for('teacher.marks'))

        ok = execute_query(
            "SELECT 1 FROM course_assignments WHERE teacher_id=%s AND course_id=%s",
            (tid, int(course_id)), fetchone=True)
        if not ok:
            flash('You are not assigned to this course.', 'danger')
            return redirect(url_for('teacher.marks'))

        eids = request.form.getlist('enrollment_ids')
        for eid in eids:
            obtained = request.form.get(f'marks_{eid}', '').strip()
            remarks  = request.form.get(f'remarks_{eid}', '').strip()
            if obtained:
                try:
                    execute_query("""
                        INSERT INTO marks
                            (enrollment_id, exam_type, obtained_marks, total_marks, remarks)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (enrollment_id, exam_type)
                        DO UPDATE SET obtained_marks = EXCLUDED.obtained_marks,
                                      total_marks   = EXCLUDED.total_marks,
                                      remarks       = EXCLUDED.remarks
                    """, (int(eid), exam_type, float(obtained),
                          float(total_marks), remarks or None))
                except Exception as e:
                    flash(f'Error saving marks: {e}', 'danger')
                    return redirect(url_for('teacher.marks',
                                            course_id=course_id, exam_type=exam_type))

        flash('Marks saved successfully.', 'success')
        return redirect(url_for('teacher.marks',
                                course_id=course_id, exam_type=exam_type))

    # GET — load students
    if sel_course and sel_exam:
        students = execute_query("""
            SELECT e.enrollment_id, s.roll_no, u.full_name, s.section,
                   m.obtained_marks, m.total_marks, m.remarks
            FROM enrollments e
            JOIN students s ON e.student_id = s.student_id
            JOIN users u    ON s.user_id    = u.user_id
            LEFT JOIN marks m
                   ON e.enrollment_id = m.enrollment_id AND m.exam_type = %s
            WHERE e.course_id = %s
            ORDER BY s.roll_no
        """, (sel_exam, int(sel_course)), fetch=True)

    return render_template('teacher/marks.html',
                           courses=courses, students=students,
                           selected_course=sel_course, selected_exam=sel_exam)


# ================================================================== #
#  Announcements (course-specific)
# ================================================================== #

@teacher_bp.route('/announcements', methods=['GET', 'POST'])
@role_required('teacher')
def announcements():
    tid = _teacher_id()
    if not tid:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        title     = request.form.get('title', '').strip()
        body      = request.form.get('body', '').strip()
        course_id = request.form.get('course_id', '').strip()

        if not all([title, body, course_id]):
            flash('Title, body, and course are required.', 'danger')
            return redirect(url_for('teacher.announcements'))

        ok = execute_query(
            "SELECT 1 FROM course_assignments WHERE teacher_id=%s AND course_id=%s",
            (tid, int(course_id)), fetchone=True)
        if not ok:
            flash('You are not assigned to this course.', 'danger')
            return redirect(url_for('teacher.announcements'))

        try:
            execute_query(
                """INSERT INTO announcements (posted_by, course_id, title, body)
                   VALUES (%s, %s, %s, %s)""",
                (session['user_id'], int(course_id), title, body))
            flash('Announcement posted.', 'success')
        except Exception as e:
            flash(f'Error posting announcement: {e}', 'danger')

        return redirect(url_for('teacher.announcements'))

    # GET — AJAX infinite scroll support
    is_ajax = request.args.get('ajax') == '1'
    q = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 10))

    params = [session['user_id']]
    where_extra = ""
    if q:
        where_extra = "AND (a.title ILIKE %s OR a.body ILIKE %s)"
        like_q = f"%{q}%"
        params.extend([like_q, like_q])

    query = f"""
        SELECT a.*, c.course_name, c.course_code
        FROM announcements a
        LEFT JOIN courses c ON a.course_id = c.course_id
        WHERE a.posted_by = %s {where_extra}
        ORDER BY a.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    my_announcements = execute_query(query, tuple(params), fetch=True)

    if is_ajax:
        html = render_template('teacher/partials/announcement_rows.html', announcements=my_announcements)
        return {"html": html, "count": len(my_announcements)}

    courses = execute_query("""
        SELECT ca.course_id, c.course_code, c.course_name
        FROM course_assignments ca
        JOIN courses c ON ca.course_id = c.course_id
        WHERE ca.teacher_id = %s
    """, (tid,), fetch=True)

    return render_template('teacher/announcements.html',
                           courses=courses, announcements=[])
