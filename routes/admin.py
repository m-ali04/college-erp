"""Admin blueprint — user/course/enrollment/assignment management."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import role_required
from models.db import execute_query

admin_bp = Blueprint('admin', __name__)


# ================================================================== #
#  Dashboard
# ================================================================== #

@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    stats = {
        'total_users':       execute_query("SELECT COUNT(*) AS c FROM users",       fetchone=True)['c'],
        'total_students':    execute_query("SELECT COUNT(*) AS c FROM students",    fetchone=True)['c'],
        'total_teachers':    execute_query("SELECT COUNT(*) AS c FROM teachers",    fetchone=True)['c'],
        'total_courses':     execute_query("SELECT COUNT(*) AS c FROM courses",     fetchone=True)['c'],
        'total_enrollments': execute_query("SELECT COUNT(*) AS c FROM enrollments", fetchone=True)['c'],
    }
    recent_announcements = execute_query("""
        SELECT a.*, u.full_name AS poster_name
        FROM announcements a
        JOIN users u ON a.posted_by = u.user_id
        ORDER BY a.created_at DESC LIMIT 5
    """, fetch=True)
    return render_template('admin/dashboard.html',
                           stats=stats, announcements=recent_announcements)


# ================================================================== #
#  User Management
# ================================================================== #

@admin_bp.route('/users')
@role_required('admin')
def manage_users():
    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    where_clause = ""
    params = []
    
    if search_query:
        where_clause = "WHERE u.full_name ILIKE %s OR u.email ILIKE %s OR u.role ILIKE %s"
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q, like_q])
        
    query = f"""
        SELECT u.*,
               s.student_id, s.roll_no, s.department AS student_dept,
               s.batch_year, s.section,
               t.teacher_id, t.employee_code, t.department AS teacher_dept,
               t.designation
        FROM users u
        LEFT JOIN students s ON u.user_id = s.user_id
        LEFT JOIN teachers t ON u.user_id = t.user_id
        {where_clause}
        ORDER BY u.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    
    users = execute_query(query, tuple(params), fetch=True)
    
    if is_ajax:
        html = render_template('admin/partials/user_rows.html', users=users)
        return {"html": html, "count": len(users)}

    return render_template('admin/manage_users.html', users=[])


@admin_bp.route('/users/create', methods=['POST'])
@role_required('admin')
def create_user():
    full_name = request.form.get('full_name', '').strip()
    email     = request.form.get('email', '').strip()
    password  = request.form.get('password', '')
    role      = request.form.get('role', '')

    if not all([full_name, email, password, role]):
        flash('All required fields must be filled.', 'danger')
        return redirect(url_for('admin.manage_users'))

    if role not in ('student', 'teacher', 'admin'):
        flash('Invalid role selected.', 'danger')
        return redirect(url_for('admin.manage_users'))

    existing = execute_query("SELECT user_id FROM users WHERE email = %s",
                             (email,), fetchone=True)
    if existing:
        flash('A user with this email already exists.', 'danger')
        return redirect(url_for('admin.manage_users'))

    try:
        user = execute_query(
            """INSERT INTO users (full_name, email, password, role)
               VALUES (%s, %s, %s, %s) RETURNING user_id""",
            (full_name, email, password, role), fetchone=True
        )
        uid = user['user_id']

        if role == 'student':
            roll_no    = request.form.get('roll_no', '').strip()
            dept       = request.form.get('s_department', '').strip()
            batch_year = request.form.get('batch_year', '').strip()
            section    = request.form.get('section', '').strip()
            execute_query(
                """INSERT INTO students (user_id, roll_no, department, batch_year, section)
                   VALUES (%s, %s, %s, %s, %s)""",
                (uid, roll_no or None, dept or None,
                 int(batch_year) if batch_year else None, section or None)
            )
        elif role == 'teacher':
            emp_code    = request.form.get('employee_code', '').strip()
            dept        = request.form.get('t_department', '').strip()
            designation = request.form.get('designation', '').strip()
            execute_query(
                """INSERT INTO teachers (user_id, employee_code, department, designation)
                   VALUES (%s, %s, %s, %s)""",
                (uid, emp_code or None, dept or None, designation or None)
            )

        flash(f'User "{full_name}" created successfully as {role}.', 'success')
    except Exception as e:
        flash(f'Error creating user: {e}', 'danger')

    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_user(user_id):
    if request.method == 'POST':
        full_name    = request.form.get('full_name', '').strip()
        email        = request.form.get('email', '').strip()
        new_password = request.form.get('password', '').strip()

        if not all([full_name, email]):
            flash('Name and email are required.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))

        dup = execute_query(
            "SELECT user_id FROM users WHERE email = %s AND user_id != %s",
            (email, user_id), fetchone=True
        )
        if dup:
            flash('Email already in use by another user.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))

        try:
            if new_password:
                execute_query(
                    "UPDATE users SET full_name=%s, email=%s, password=%s WHERE user_id=%s",
                    (full_name, email, new_password, user_id))
            else:
                execute_query(
                    "UPDATE users SET full_name=%s, email=%s WHERE user_id=%s",
                    (full_name, email, user_id))

            user_role = execute_query(
                "SELECT role FROM users WHERE user_id=%s", (user_id,), fetchone=True
            )['role']

            if user_role == 'student':
                execute_query(
                    """UPDATE students
                       SET roll_no=%s, department=%s, batch_year=%s, section=%s
                       WHERE user_id=%s""",
                    (request.form.get('roll_no', '').strip() or None,
                     request.form.get('s_department', '').strip() or None,
                     int(request.form['batch_year']) if request.form.get('batch_year', '').strip() else None,
                     request.form.get('section', '').strip() or None,
                     user_id)
                )
            elif user_role == 'teacher':
                execute_query(
                    """UPDATE teachers
                       SET employee_code=%s, department=%s, designation=%s
                       WHERE user_id=%s""",
                    (request.form.get('employee_code', '').strip() or None,
                     request.form.get('t_department', '').strip() or None,
                     request.form.get('designation', '').strip() or None,
                     user_id)
                )

            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            flash(f'Error updating user: {e}', 'danger')

    # GET — fetch current data
    user = execute_query("""
        SELECT u.*,
               s.student_id, s.roll_no, s.department AS student_dept,
               s.batch_year, s.section,
               t.teacher_id, t.employee_code, t.department AS teacher_dept,
               t.designation
        FROM users u
        LEFT JOIN students s ON u.user_id = s.user_id
        LEFT JOIN teachers t ON u.user_id = t.user_id
        WHERE u.user_id = %s
    """, (user_id,), fetchone=True)

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.manage_users'))

    return render_template('admin/edit_user.html', user=user)


# ================================================================== #
#  Course Management
# ================================================================== #

@admin_bp.route('/courses')
@role_required('admin')
def manage_courses():
    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    where_clause = ""
    params = []
    
    if search_query:
        where_clause = "WHERE course_code ILIKE %s OR course_name ILIKE %s OR department ILIKE %s"
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q, like_q])
        
    query = f"""
        SELECT * FROM courses
        {where_clause}
        ORDER BY course_code
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    
    courses = execute_query(query, tuple(params), fetch=True)
    
    if is_ajax:
        html = render_template('admin/partials/course_rows.html', courses=courses)
        return {"html": html, "count": len(courses)}

    return render_template('admin/manage_courses.html', courses=[])


@admin_bp.route('/courses/create', methods=['POST'])
@role_required('admin')
def create_course():
    code   = request.form.get('course_code', '').strip()
    name   = request.form.get('course_name', '').strip()
    hours  = request.form.get('credit_hours', '').strip()
    dept   = request.form.get('department', '').strip()

    if not all([code, name, hours]):
        flash('Course code, name, and credit hours are required.', 'danger')
        return redirect(url_for('admin.manage_courses'))

    try:
        hours = int(hours)
        if hours <= 0:
            raise ValueError()
    except ValueError:
        flash('Credit hours must be a positive integer.', 'danger')
        return redirect(url_for('admin.manage_courses'))

    try:
        execute_query(
            """INSERT INTO courses (course_code, course_name, credit_hours, department)
               VALUES (%s, %s, %s, %s)""",
            (code, name, hours, dept or None))
        flash(f'Course "{code} — {name}" created.', 'success')
    except Exception as e:
        if 'unique' in str(e).lower():
            flash('A course with this code already exists.', 'danger')
        else:
            flash(f'Error creating course: {e}', 'danger')

    return redirect(url_for('admin.manage_courses'))


@admin_bp.route('/courses/<int:course_id>/edit', methods=['POST'])
@role_required('admin')
def edit_course(course_id):
    code  = request.form.get('course_code', '').strip()
    name  = request.form.get('course_name', '').strip()
    hours = request.form.get('credit_hours', '').strip()
    dept  = request.form.get('department', '').strip()

    if not all([code, name, hours]):
        flash('Course code, name, and credit hours are required.', 'danger')
        return redirect(url_for('admin.manage_courses'))

    try:
        execute_query(
            """UPDATE courses
               SET course_code=%s, course_name=%s, credit_hours=%s, department=%s
               WHERE course_id=%s""",
            (code, name, int(hours), dept or None, course_id))
        flash('Course updated.', 'success')
    except Exception as e:
        flash(f'Error updating course: {e}', 'danger')

    return redirect(url_for('admin.manage_courses'))


# ================================================================== #
#  Enrollment Management
# ================================================================== #

@admin_bp.route('/enrollments')
@role_required('admin')
def manage_enrollments():
    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    where_clause = ""
    params = []
    
    if search_query:
        where_clause = "WHERE u.full_name ILIKE %s OR s.roll_no ILIKE %s OR c.course_name ILIKE %s"
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q, like_q])
        
    query = f"""
        SELECT e.*, s.roll_no, u.full_name,
               c.course_code, c.course_name
        FROM enrollments e
        JOIN students s ON e.student_id = s.student_id
        JOIN users u    ON s.user_id    = u.user_id
        JOIN courses c  ON e.course_id  = c.course_id
        {where_clause}
        ORDER BY e.academic_year DESC, e.semester, c.course_code
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    
    enrollments = execute_query(query, tuple(params), fetch=True)

    if is_ajax:
        html = render_template('admin/partials/enrollment_rows.html', enrollments=enrollments)
        return {"html": html, "count": len(enrollments)}

    students = execute_query("""
        SELECT s.student_id, s.roll_no, u.full_name
        FROM students s JOIN users u ON s.user_id = u.user_id
        ORDER BY s.roll_no
    """, fetch=True)

    courses = execute_query("SELECT * FROM courses ORDER BY course_code", fetch=True)

    return render_template('admin/manage_enrollments.html',
                           enrollments=[], students=students, courses=courses)


@admin_bp.route('/enrollments/create', methods=['POST'])
@role_required('admin')
def create_enrollment():
    sid   = request.form.get('student_id', '').strip()
    cid   = request.form.get('course_id', '').strip()
    sem   = request.form.get('semester', '').strip()
    year  = request.form.get('academic_year', '').strip()

    if not all([sid, cid, sem, year]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin.manage_enrollments'))

    try:
        execute_query(
            """INSERT INTO enrollments (student_id, course_id, semester, academic_year)
               VALUES (%s, %s, %s, %s)""",
            (int(sid), int(cid), sem, year))
        flash('Student enrolled successfully.', 'success')
    except Exception as e:
        flash(f'Error creating enrollment: {e}', 'danger')

    return redirect(url_for('admin.manage_enrollments'))


@admin_bp.route('/enrollments/<int:enrollment_id>/delete', methods=['POST'])
@role_required('admin')
def delete_enrollment(enrollment_id):
    try:
        execute_query("DELETE FROM enrollments WHERE enrollment_id = %s",
                      (enrollment_id,))
        flash('Enrollment removed.', 'success')
    except Exception as e:
        flash(f'Cannot delete enrollment (it may have linked attendance/marks): {e}', 'danger')
    return redirect(url_for('admin.manage_enrollments'))


# ================================================================== #
#  Course Assignment Management
# ================================================================== #

@admin_bp.route('/assignments')
@role_required('admin')
def manage_assignments():
    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    where_clause = ""
    params = []
    
    if search_query:
        where_clause = "WHERE u.full_name ILIKE %s OR t.employee_code ILIKE %s OR c.course_name ILIKE %s"
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q, like_q])
        
    query = f"""
        SELECT ca.*, t.employee_code, u.full_name,
               c.course_code, c.course_name
        FROM course_assignments ca
        JOIN teachers t ON ca.teacher_id = t.teacher_id
        JOIN users u    ON t.user_id     = u.user_id
        JOIN courses c  ON ca.course_id  = c.course_id
        {where_clause}
        ORDER BY ca.academic_year DESC, ca.semester, c.course_code
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    
    assignments = execute_query(query, tuple(params), fetch=True)
    
    if is_ajax:
        html = render_template('admin/partials/assignment_rows.html', assignments=assignments)
        return {"html": html, "count": len(assignments)}

    teachers = execute_query("""
        SELECT t.teacher_id, t.employee_code, u.full_name
        FROM teachers t JOIN users u ON t.user_id = u.user_id
        ORDER BY u.full_name
    """, fetch=True)

    courses = execute_query("SELECT * FROM courses ORDER BY course_code", fetch=True)

    return render_template('admin/manage_assignments.html',
                           assignments=[], teachers=teachers, courses=courses)


@admin_bp.route('/assignments/create', methods=['POST'])
@role_required('admin')
def create_assignment():
    tid  = request.form.get('teacher_id', '').strip()
    cid  = request.form.get('course_id', '').strip()
    sem  = request.form.get('semester', '').strip()
    year = request.form.get('academic_year', '').strip()

    if not all([tid, cid, sem, year]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin.manage_assignments'))

    try:
        execute_query(
            """INSERT INTO course_assignments (teacher_id, course_id, semester, academic_year)
               VALUES (%s, %s, %s, %s)""",
            (int(tid), int(cid), sem, year))
        flash('Course assigned to teacher successfully.', 'success')
    except Exception as e:
        flash(f'Error creating assignment: {e}', 'danger')

    return redirect(url_for('admin.manage_assignments'))


@admin_bp.route('/assignments/<int:assignment_id>/delete', methods=['POST'])
@role_required('admin')
def delete_assignment(assignment_id):
    try:
        execute_query("DELETE FROM course_assignments WHERE assignment_id = %s",
                      (assignment_id,))
        flash('Assignment removed.', 'success')
    except Exception as e:
        flash(f'Cannot delete assignment: {e}', 'danger')
    return redirect(url_for('admin.manage_assignments'))


# ================================================================== #
#  Announcements (system-wide, course_id = NULL)
# ================================================================== #

@admin_bp.route('/announcements')
@role_required('admin')
def announcements():
    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    where_clause = ""
    params = []
    
    if search_query:
        where_clause = "WHERE a.title ILIKE %s OR a.body ILIKE %s OR u.full_name ILIKE %s"
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q, like_q])
        
    query = f"""
        SELECT a.*, u.full_name AS poster_name,
               c.course_name, c.course_code
        FROM announcements a
        JOIN users u ON a.posted_by = u.user_id
        LEFT JOIN courses c ON a.course_id = c.course_id
        {where_clause}
        ORDER BY a.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    
    rows = execute_query(query, tuple(params), fetch=True)
    
    if is_ajax:
        html = render_template('admin/partials/announcement_rows.html', announcements=rows)
        return {"html": html, "count": len(rows)}

    return render_template('admin/announcements.html', announcements=[])


@admin_bp.route('/announcements/create', methods=['POST'])
@role_required('admin')
def create_announcement():
    title = request.form.get('title', '').strip()
    body  = request.form.get('body', '').strip()

    if not all([title, body]):
        flash('Title and body are required.', 'danger')
        return redirect(url_for('admin.announcements'))

    try:
        execute_query(
            """INSERT INTO announcements (posted_by, course_id, title, body)
               VALUES (%s, NULL, %s, %s)""",
            (session['user_id'], title, body))
        flash('Announcement posted.', 'success')
    except Exception as e:
        flash(f'Error posting announcement: {e}', 'danger')

    return redirect(url_for('admin.announcements'))


# ================================================================== #
#  Fee Management
# ================================================================== #

@admin_bp.route('/fees')
@role_required('admin')
def manage_fees():
    execute_query("UPDATE student_fees SET status = 'overdue' WHERE status = 'pending' AND due_date < CURRENT_DATE")
    
    is_ajax = request.args.get('ajax') == '1'
    search_query = request.args.get('q', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    where_clause = ""
    params = []
    
    if search_query:
        where_clause = "WHERE u.full_name ILIKE %s OR s.roll_no ILIKE %s OR f.fee_type ILIKE %s"
        like_q = f"%{search_query}%"
        params.extend([like_q, like_q, like_q])
        
    query = f"""
        SELECT f.*, s.roll_no, u.full_name
        FROM student_fees f
        JOIN students s ON f.student_id = s.student_id
        JOIN users u ON s.user_id = u.user_id
        {where_clause}
        ORDER BY f.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    
    fees = execute_query(query, tuple(params), fetch=True)
    
    if is_ajax:
        html = render_template('admin/partials/fee_rows.html', fees=fees)
        return {"html": html, "count": len(fees)}
    
    students = execute_query("""
        SELECT s.student_id, s.roll_no, u.full_name
        FROM students s JOIN users u ON s.user_id = u.user_id
        ORDER BY s.roll_no
    """, fetch=True)
    
    return render_template('admin/manage_fees.html', fees=[], students=students)

@admin_bp.route('/fees/create', methods=['POST'])
@role_required('admin')
def create_fee():
    sid      = request.form.get('student_id', '').strip()
    fee_type = request.form.get('fee_type', '').strip()
    amount   = request.form.get('amount', '').strip()
    due_date = request.form.get('due_date', '').strip()

    if not all([sid, fee_type, amount, due_date]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin.manage_fees'))

    try:
        execute_query(
            """INSERT INTO student_fees (student_id, fee_type, amount, due_date)
               VALUES (%s, %s, %s, %s)""",
            (int(sid), fee_type, float(amount), due_date))
        flash('Fee record created successfully.', 'success')
    except Exception as e:
        flash(f'Error creating fee: {e}', 'danger')

    return redirect(url_for('admin.manage_fees'))

@admin_bp.route('/fees/<int:fee_id>/mark_paid', methods=['POST'])
@role_required('admin')
def mark_fee_paid(fee_id):
    try:
        execute_query(
            "UPDATE student_fees SET status = 'paid', payment_date = CURRENT_DATE WHERE fee_id = %s",
            (fee_id,)
        )
        flash('Fee marked as paid.', 'success')
    except Exception as e:
        flash(f'Error updating fee: {e}', 'danger')
    return redirect(url_for('admin.manage_fees'))

@admin_bp.route('/fees/<int:fee_id>/delete', methods=['POST'])
@role_required('admin')
def delete_fee(fee_id):
    try:
        execute_query("DELETE FROM student_fees WHERE fee_id = %s", (fee_id,))
        flash('Fee deleted successfully.', 'success')
    except Exception as e:
        flash(f'Cannot delete fee: {e}', 'danger')
    return redirect(url_for('admin.manage_fees'))
