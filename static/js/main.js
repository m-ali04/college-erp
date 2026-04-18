/* College ERP — Client-side helpers */

// Sidebar toggle (mobile)
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', function (e) {
    var sb = document.getElementById('sidebar');
    var btn = document.getElementById('menuToggle');
    if (sb && sb.classList.contains('open') && !sb.contains(e.target) && e.target !== btn) {
        sb.classList.remove('open');
    }
});

// Auto-dismiss alerts after 5 s
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.alert').forEach(function (el) {
        setTimeout(function () {
            el.style.animation = 'slideOut .3s ease forwards';
            setTimeout(function () { el.remove(); }, 300);
        }, 5000);
    });

    // Role-specific field toggle
    var rs = document.getElementById('roleSelect');
    if (rs) {
        rs.addEventListener('change', toggleRoleFields);
        toggleRoleFields();
    }
});

function toggleRoleFields() {
    var role = document.getElementById('roleSelect').value;
    var sf = document.getElementById('studentFields');
    var tf = document.getElementById('teacherFields');
    if (sf) sf.style.display = (role === 'student') ? 'block' : 'none';
    if (tf) tf.style.display = (role === 'teacher') ? 'block' : 'none';
}

function confirmDelete(form, name) {
    if (confirm('Are you sure you want to remove this ' + name + '?')) form.submit();
}

// Theme Toggle Logic
document.addEventListener('DOMContentLoaded', function () {
    const themeToggleBtns = document.querySelectorAll('.theme-toggle-btn');
    const currentTheme = localStorage.getItem('theme') || 'dark';

    function updateIcons(theme) {
        themeToggleBtns.forEach(btn => {
            const icon = btn.querySelector('i');
            if (theme === 'light') {
                icon.classList.remove('fa-sun');
                icon.classList.add('fa-moon');
            } else {
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            }
        });
    }

    updateIcons(currentTheme);

    themeToggleBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            let newTheme = 'dark';
            if (document.documentElement.getAttribute('data-theme') !== 'light') {
                newTheme = 'light';
                document.documentElement.setAttribute('data-theme', 'light');
            } else {
                document.documentElement.removeAttribute('data-theme');
            }
            localStorage.setItem('theme', newTheme);
            updateIcons(newTheme);
        });
    });
});
