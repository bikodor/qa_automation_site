const dialog = document.querySelector('#delete-dialog');
document.querySelector('#open-delete')?.addEventListener('click', () => dialog.showModal());
document.querySelector('#cancel-delete')?.addEventListener('click', () => dialog.close());

let csrfToken;
async function api(url, {method = 'GET', body, signal} = {}) {
    const headers = {Accept: 'application/json'};
    if (method !== 'GET') {
        if (!csrfToken) {
            const tokenData = await api('/api/auth/csrf/');
            csrfToken = tokenData.csrfToken;
        }
        headers['X-CSRFToken'] = csrfToken;
        headers['Content-Type'] = 'application/json';
    }
    const response = await fetch(url, {
        method, headers, credentials: 'same-origin', signal,
        body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = response.status === 204 ? {} : await response.json();
    if (!response.ok) {
        if (data.error?.code === 'csrf_failed') csrfToken = null;
        const failure = new Error(data.error?.message || 'Request failed. Please try again.');
        failure.fields = data.error?.fields || {};
        failure.status = response.status;
        throw failure;
    }
    if (data.csrfToken) csrfToken = data.csrfToken;
    return data;
}

function element(tag, text, className, testId) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    if (testId) node.dataset.testid = testId;
    return node;
}

function showError(container, failure) {
    const summary = element('div', failure.message || 'Network error. Please try again.', 'errors', 'form-errors');
    summary.setAttribute('role', 'alert');
    container.prepend(summary);
    let firstInput;
    for (const [name, errors] of Object.entries(failure.fields || {})) {
        const input = container.elements?.namedItem(name);
        const field = input?.closest('.field');
        if (!field) {
            summary.append(element('div', errors.join(' ')));
            continue;
        }
        field.classList.add('invalid');
        const message = element('div', errors.join(' '), 'errors', `error-${name}`);
        message.id = `api-error-${name}`;
        message.setAttribute('role', 'alert');
        field.append(message);
        input.setAttribute('aria-invalid', 'true');
        input.setAttribute('aria-errormessage', message.id);
        firstInput ||= input;
    }
    firstInput?.focus();
}

function clearErrors(container) {
    container.querySelectorAll('.errors').forEach(node => node.remove());
    container.querySelectorAll('.invalid').forEach(node => node.classList.remove('invalid'));
    container.querySelectorAll('[aria-invalid]').forEach(node => {
        node.removeAttribute('aria-invalid');
        node.removeAttribute('aria-errormessage');
    });
}

function rememberNotice(message) {
    try { sessionStorage.setItem('practice-notice', message); } catch (_) { /* Storage may be disabled. */ }
}
try {
    const message = sessionStorage.getItem('practice-notice');
    if (message) {
        sessionStorage.removeItem('practice-notice');
        const notice = element('div', message, 'notice', 'notification');
        notice.setAttribute('role', 'status');
        document.querySelector('main').prepend(notice);
    }
} catch (_) { /* Storage may be disabled. */ }

function connectForm(form, url, method = 'POST', fallback = '/tasks/') {
    if (!form) return;
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (form.getAttribute('aria-busy') === 'true') return;
        clearErrors(form);
        const button = form.querySelector('button:not([type="button"])');
        const label = button.textContent;
        button.disabled = true;
        button.textContent = 'Please wait…';
        form.setAttribute('aria-busy', 'true');
        const formData = new FormData(form);
        const body = Object.fromEntries(formData);
        delete body.csrfmiddlewaretoken;
        delete body.action;
        if (form.elements.namedItem('terms')) body.terms = form.elements.namedItem('terms').checked;
        if (url === '/api/auth/login/') body.next = new URLSearchParams(location.search).get('next') || '/tasks/';
        if (form.dataset.testid === 'task-form') {
            body.project_id = body.project ? Number(body.project) : null;
            body.label_ids = formData.getAll('labels').map(Number);
            delete body.project;
            delete body.labels;
        }
        try {
            const data = await api(url, {method, body: method === 'DELETE' ? undefined : body});
            rememberNotice(data.message || 'Deleted successfully.');
            location.assign(data.redirect_url || fallback);
        } catch (failure) {
            showError(form, failure);
        } finally {
            button.disabled = false;
            button.textContent = label;
            form.setAttribute('aria-busy', 'false');
        }
    });
}

connectForm(document.querySelector('[data-testid="register-form"]'), '/api/auth/register/');
connectForm(document.querySelector('[data-testid="login-form"]'), '/api/auth/login/');
connectForm(document.querySelector('[data-testid="logout"]')?.closest('form'), '/api/auth/logout/');
const taskId = location.pathname.match(/^\/tasks\/(\d+)\//)?.[1];
connectForm(document.querySelector('[data-testid="task-form"]'),
    taskId ? `/api/tasks/${taskId}/` : '/api/tasks/', taskId ? 'PUT' : 'POST');
connectForm(dialog?.querySelector('form'), `/api/tasks/${taskId}/`, 'DELETE');
connectForm(document.querySelector('[data-testid="project-form"]'), '/api/projects/', 'POST', '/projects/');
connectForm(document.querySelector('[data-testid="label-form"]'), '/api/labels/', 'POST', '/projects/');
document.querySelectorAll('[data-api-delete]').forEach(form => {
    connectForm(form, form.dataset.apiDelete, 'DELETE', '/projects/');
});

function displayDate(value) {
    return value ? value.split('-').reverse().join('.') : 'No due date';
}

// Search, sorting and pagination replace the list without a document navigation.
const filters = document.querySelector('[data-testid="filters"]');
if (filters) {
    const list = document.querySelector('[data-testid="task-list"]');
    let pagination = document.querySelector('.pagination');
    if (!pagination) {
        pagination = element('nav', undefined, 'pagination');
        pagination.setAttribute('aria-label', 'Pages');
        list.after(pagination);
    }
    let controller;
    async function loadTasks(params, push = false) {
        controller?.abort();
        const current = new AbortController();
        controller = current;
        clearErrors(filters);
        list.setAttribute('aria-busy', 'true');
        try {
            const data = await api(`/api/tasks/?${params}`, {signal: current.signal});
            const rows = data.results.map(task => {
                const row = element('a', undefined, 'task-row', 'task-row');
                row.href = task.url;
                row.dataset.taskId = task.id;
                row.append(element('span', task.status === 'done' ? '✓' : '',
                    `task-mark ${task.status === 'done' ? 'checked' : ''}`));
                const name = element('div', undefined, 'task-name');
                name.append(element('strong', task.title), element('small',
                    `${task.project ? task.project.name + ' · ' : ''}${task.due_date ? `Due ${displayDate(task.due_date)}` : 'No due date'}`));
                if (task.labels.length) {
                    const chips = element('span', undefined, 'row-labels');
                    for (const label of task.labels) chips.append(element('span', label.name, `label-chip ${label.color}`));
                    name.append(chips);
                }
                row.append(name, element('span', task.priority_label, `priority ${task.priority}`),
                    element('span', task.status_label, `badge ${task.status}`), element('span', '↗', 'arrow'));
                return row;
            });
            if (!rows.length) {
                const empty = element('div', undefined, 'empty', 'empty-state');
                empty.append(element('h2', data.stats.total ? 'No matches' : 'Start with one task'),
                    element('p', data.stats.total ? 'Try changing your search or resetting the filters.' : 'Big plans start with a small step.'));
                const action = element('a', data.stats.total ? 'Reset filters' : 'Create a task', 'button secondary');
                action.href = data.stats.total ? '/tasks/' : '/tasks/new/';
                if (data.stats.total) action.addEventListener('click', event => {
                    event.preventDefault();
                    loadTasks(new URLSearchParams(), true);
                });
                empty.append(action);
                rows.push(empty);
            }
            list.replaceChildren(...rows);
            document.querySelector('[data-testid="result-count"]').textContent = `Found: ${data.count}`;
            for (const key of ['total', 'active', 'done']) {
                document.querySelector(`[data-testid="${key}-count"]`).textContent = data.stats[key];
            }
            pagination.replaceChildren();
            if (data.pages > 1) {
                for (const direction of ['previous', 'next']) {
                    if (direction === 'next') pagination.append(element('span', `${data.page} / ${data.pages}`, '', 'page-number'));
                    if (!data[direction]) continue;
                    const target = new URLSearchParams(params);
                    target.set('page', data[direction]);
                    const link = element('a', direction === 'previous' ? '← Previous' : 'Next →', 'button secondary small', `${direction}-page`);
                    link.href = `?${target}`;
                    link.addEventListener('click', event => {
                        event.preventDefault();
                        loadTasks(target, true);
                    });
                    pagination.append(link);
                }
            }
            for (const key of ['q', 'status', 'priority', 'project_id', 'label_id', 'sort']) {
                filters.elements.namedItem(key).value = params.get(key) || (key === 'sort' ? 'newest' : '');
            }
            if (push) history.pushState(null, '', `/tasks/${params.size ? '?' + params : ''}`);
        } catch (failure) {
            if (failure.name !== 'AbortError') showError(filters, failure);
        } finally {
            if (controller === current) list.setAttribute('aria-busy', 'false');
        }
    }
    filters.addEventListener('submit', event => {
        event.preventDefault();
        loadTasks(new URLSearchParams(new FormData(filters)), true);
    });
    document.querySelector('[data-testid="reset-filters"]').addEventListener('click', event => {
        event.preventDefault();
        loadTasks(new URLSearchParams(), true);
    });
    addEventListener('popstate', () => loadTasks(new URLSearchParams(location.search)));
    loadTasks(new URLSearchParams(location.search));
}

// Refresh the detail card from its JSON resource as well.
if (taskId && dialog) {
    api(`/api/tasks/${taskId}/`).then(({task}) => {
        document.querySelector('[data-testid="task-title"]').textContent = task.title;
        const description = document.querySelector('[data-testid="task-description"]');
        description.textContent = task.description || 'No description added.';
        description.style.whiteSpace = 'pre-wrap';
        document.querySelector('[data-testid="task-due-date"]').textContent = displayDate(task.due_date);
        document.querySelector('[data-testid="task-project"]').textContent = task.project?.name || 'Unassigned';
        const labels = document.querySelector('[data-testid="task-labels"]');
        labels.replaceChildren(...(task.labels.length
            ? task.labels.map(label => element('span', label.name, `label-chip ${label.color}`))
            : [document.createTextNode('No labels')]));
        const status = document.querySelector('[data-testid="task-status"]');
        status.textContent = task.status_label;
        status.className = `badge ${task.status}`;
        const priority = document.querySelector('[data-testid="task-priority"]');
        priority.textContent = `${task.priority_label} priority`;
        priority.className = `priority ${task.priority}`;
    }).catch(failure => showError(document.querySelector('.detail'), failure));
}
