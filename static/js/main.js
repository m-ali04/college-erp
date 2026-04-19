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

// Infinite Scroll & Search
document.addEventListener('DOMContentLoaded', function () {
    const tableContainer = document.getElementById('infinite-scroll-container');
    if (!tableContainer) return;

    const containerBody = document.getElementById('infinite-table-body');
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const dataUrl = tableContainer.getAttribute('data-url');
    
    let offset = 0;
    const limit = 20;
    let currentQuery = '';
    let isLoading = false;
    let hasMore = true;

    function getEmptyMessage(msg, isTable) {
        if (isTable) {
            return `<tr><td colspan="10" style="text-align:center; padding: 20px;">${msg}</td></tr>`;
        }
        return `<div style="text-align:center; padding: 20px; width: 100%;">${msg}</div>`;
    }

    function loadRecords(reset = false) {
        if (isLoading || (!hasMore && !reset)) return;
        isLoading = true;
        const isTable = containerBody.tagName === 'TBODY';

        if (reset) {
            offset = 0;
            hasMore = true;
            containerBody.innerHTML = getEmptyMessage('<i class="fas fa-spinner fa-spin"></i> Loading...', isTable);
        }

        const url = new URL(dataUrl, window.location.origin);
        url.searchParams.set('q', currentQuery);
        url.searchParams.set('offset', offset);
        url.searchParams.set('limit', limit);
        url.searchParams.set('ajax', '1');

        fetch(url)
            .then(r => r.json())
            .then(data => {
                if (reset) containerBody.innerHTML = '';
                
                if (data.count < limit) {
                    hasMore = false;
                }
                offset += data.count;

                if (data.html) {
                    containerBody.insertAdjacentHTML('beforeend', data.html);
                }
                
                if (data.count === 0 && reset) {
                    containerBody.innerHTML = getEmptyMessage('No records found.', isTable);
                }
                isLoading = false;
            })
            .catch(err => {
                console.error(err);
                if (reset) containerBody.innerHTML = getEmptyMessage('Error loading records.', isTable);
                isLoading = false;
            });
    }

    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', () => {
            currentQuery = searchInput.value.trim();
            loadRecords(true);
        });
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                currentQuery = searchInput.value.trim();
                loadRecords(true);
            }
        });
    }

    // Scroll listener on container
    tableContainer.addEventListener('scroll', () => {
        if (tableContainer.scrollTop + tableContainer.clientHeight >= tableContainer.scrollHeight - 50) {
            loadRecords(false);
        }
    });

    // Initial load
    loadRecords(true);
});
