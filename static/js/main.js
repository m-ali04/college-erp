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

/* ================================================================
   SEARCHABLE SELECT — vanilla JS combobox
   Upgrades every <select class="searchable"> automatically.
   ================================================================ */

class SearchableSelect {
    constructor(selectEl) {
        this.select  = selectEl;
        this.options = Array.from(selectEl.options);
        this.focused = -1;
        this._isOpen = false;
        this._visibleOptions = [];
        this._build();
        this._bind();

        // Restore initial value if the select already had one pre-upgrade
        const initOpt = this.options.find(o => o.value === selectEl.value && o.value !== '');
        if (initOpt) this._setDisplay(initOpt.value, initOpt.text);
    }

    _build() {
        const sel = this.select;

        // Wrap the native select
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'ss-wrapper';
        sel.parentNode.insertBefore(this.wrapper, sel);
        this.wrapper.appendChild(sel);
        sel.style.display = 'none';

        // Trigger button (the visible "fake select")
        this.trigger = document.createElement('button');
        this.trigger.type = 'button';
        this.trigger.className = 'ss-trigger';
        this.trigger.setAttribute('aria-haspopup', 'listbox');
        this.trigger.setAttribute('aria-expanded', 'false');

        this.selectedText = document.createElement('span');
        this.selectedText.className = 'ss-selected-text placeholder';
        const placeholder = (this.options.find(o => o.value === '') || {}).text || 'Select…';
        this.selectedText.textContent = placeholder;
        this._placeholder = placeholder;

        const arrow = document.createElement('i');
        arrow.className = 'ss-arrow fas fa-chevron-down';

        this.trigger.appendChild(this.selectedText);
        this.trigger.appendChild(arrow);
        this.wrapper.appendChild(this.trigger);

        // Dropdown panel (hidden by default via CSS display:none)
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'ss-dropdown';

        // Search input row
        const searchWrap = document.createElement('div');
        searchWrap.className = 'ss-search-wrap';

        const searchIcon = document.createElement('i');
        //searchIcon.className = 'ss-search-icon fas fa-search';

        this.searchInput = document.createElement('input');
        this.searchInput.type = 'text';
        this.searchInput.className = 'ss-search';
        this.searchInput.placeholder = 'Search…';
        this.searchInput.setAttribute('autocomplete', 'off');

        searchWrap.appendChild(searchIcon);
        searchWrap.appendChild(this.searchInput);

        // Options container
        this.optionsList = document.createElement('div');
        this.optionsList.className = 'ss-options';
        this.optionsList.setAttribute('role', 'listbox');

        this.dropdown.appendChild(searchWrap);
        this.dropdown.appendChild(this.optionsList);
        this.wrapper.appendChild(this.dropdown);
    }

    /* ---- Render / filter options ---- */
    _renderOptions(query) {
        this.optionsList.innerHTML = '';
        this.focused = -1;
        const q = (query || '').toLowerCase().trim();
        const filtered = this.options.filter(o => o.value !== '' && o.text.toLowerCase().includes(q));

        if (filtered.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'ss-no-results';
            empty.innerHTML = '<i class="fas fa-search"></i>No options found';
            this.optionsList.appendChild(empty);
            this._visibleOptions = [];
            return;
        }

        filtered.forEach(opt => {
            const div = document.createElement('div');
            div.className = 'ss-option' + (opt.value === this.select.value ? ' selected' : '');
            div.setAttribute('role', 'option');
            div.setAttribute('data-value', opt.value);
            div.innerHTML = q ? this._highlight(opt.text, q) : opt.text;

            // Use 'click' so it fires AFTER the outside mousedown guard runs
            div.addEventListener('click', () => {
                this._setValue(opt.value, opt.text);
                this._close();
            });

            this.optionsList.appendChild(div);
        });

        this._visibleOptions = Array.from(this.optionsList.querySelectorAll('.ss-option'));
    }

    _highlight(text, query) {
        const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return text.replace(new RegExp(`(${escaped})`, 'gi'), '<mark>$1</mark>');
    }

    /* ---- Value helpers ---- */
    _setValue(value, text) {
        this.select.value = value;
        this.select.dispatchEvent(new Event('change', { bubbles: true }));
        this._setDisplay(value, text);
        this._renderOptions(this.searchInput.value); // refresh checkmark
    }

    _setDisplay(value, text) {
        this.selectedText.textContent = text;
        this.selectedText.classList.remove('placeholder');
    }

    /* ---- Open / close ---- */
    _open() {
        this._isOpen = true;
        this.dropdown.classList.add('visible');
        this.trigger.classList.add('open');
        this.trigger.setAttribute('aria-expanded', 'true');
        this.searchInput.value = '';
        this._renderOptions('');
        // Focus the search input after the dropdown is painted
        requestAnimationFrame(() => this.searchInput.focus());
    }

    _close() {
        this._isOpen = false;
        this.dropdown.classList.remove('visible');
        this.trigger.classList.remove('open');
        this.trigger.setAttribute('aria-expanded', 'false');
    }

    /* ---- Keyboard navigation ---- */
    _moveFocus(dir) {
        const opts = this._visibleOptions;
        if (!opts.length) return;
        opts.forEach(o => o.classList.remove('focused'));
        this.focused = Math.max(0, Math.min(opts.length - 1, this.focused + dir));
        opts[this.focused].classList.add('focused');
        opts[this.focused].scrollIntoView({ block: 'nearest' });
    }

    /* ---- Event binding ---- */
    _bind() {
        // Toggle open/close on trigger button
        this.trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            this._isOpen ? this._close() : this._open();
        });

        // Live filter
        this.searchInput.addEventListener('input', () => {
            this._renderOptions(this.searchInput.value);
        });

        // Arrow keys + Enter + Escape inside the search box
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                this._moveFocus(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this._moveFocus(-1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                const focused = this._visibleOptions[this.focused];
                if (focused) focused.click();
            } else if (e.key === 'Escape') {
                this._close();
                this.trigger.focus();
            }
        });

        // Close when clicking outside this widget
        document.addEventListener('mousedown', (e) => {
            if (this._isOpen && !this.wrapper.contains(e.target)) {
                this._close();
            }
        });
    }
}

// Auto-upgrade all <select class="searchable"> on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('select.searchable').forEach(sel => new SearchableSelect(sel));
});

