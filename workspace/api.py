import json
from functools import wraps

from django.contrib.auth import get_user_model, login, logout
from django.core.paginator import EmptyPage, Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.csrf import csrf_failure as html_csrf_failure

from .forms import LabelForm, LoginForm, ProjectForm, RegisterForm, TaskForm
from .models import Label, Project, Task


def error(code, message, status=400, fields=None):
    detail = {'code': code, 'message': message}
    if fields is not None:
        detail['fields'] = fields
    return JsonResponse({'error': detail}, status=status)


def invalid(form, status=400):
    return error('validation_error', 'Please correct the highlighted fields.', status,
                 {name: [str(message) for message in errors] for name, errors in form.errors.items()})


def endpoint(methods, *, private=False, fields=()):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = error('method_not_allowed', 'Method not allowed.', 405)
                response['Allow'] = ', '.join(methods)
                return response
            if private and not request.user.is_authenticated:
                return error('authentication_required', 'Log in to continue.', 401)
            request.api_data = {}
            if request.method in ('POST', 'PUT', 'PATCH'):
                if request.content_type != 'application/json':
                    return error('unsupported_media_type', 'Use Content-Type: application/json.', 415)
                try:
                    data = json.loads(request.body)
                except (ValueError, UnicodeDecodeError):
                    return error('invalid_json', 'The request body must be valid JSON.')
                if not isinstance(data, dict):
                    return error('invalid_json', 'The request body must be a JSON object.')
                problems = {}
                for name, value in data.items():
                    if name not in fields:
                        problems[name] = ['Unknown field.']
                    elif name == 'terms':
                        if type(value) is not bool:
                            problems[name] = ['Use a JSON boolean.']
                    elif name == 'project_id':
                        if value is not None and type(value) is not int:
                            problems[name] = ['Use an integer or null.']
                    elif name == 'label_ids':
                        if not isinstance(value, list) or any(type(item) is not int for item in value):
                            problems[name] = ['Use an array of integers.']
                    elif not isinstance(value, str) and not (name in ('description', 'due_date') and value is None):
                        problems[name] = ['Use a string.']
                if problems:
                    return error('validation_error', 'Invalid fields.', fields=problems)
                request.api_data = data
            response = view(request, *args, **kwargs)
            response['Cache-Control'] = 'no-store'
            return response
        return wrapped
    return decorate


def csrf_failure(request, reason=''):
    if request.path.startswith('/api/'):
        return error('csrf_failed', 'Refresh the CSRF token and try again.', 403)
    return html_csrf_failure(request, reason=reason)


def user_data(user):
    return {'id': user.pk, 'username': user.username, 'email': user.email}


def task_data(task):
    project = None if task.project is None else {'id': task.project_id, 'name': task.project.name}
    labels = [{'id': label.pk, 'name': label.name, 'color': label.color} for label in task.labels.all()]
    return {'id': task.pk, 'title': task.title, 'description': task.description,
            'status': task.status, 'status_label': task.get_status_display(),
            'priority': task.priority, 'priority_label': task.get_priority_display(),
            'project': project, 'project_id': task.project_id, 'labels': labels,
            'label_ids': [label['id'] for label in labels],
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_at': task.created_at.isoformat(), 'url': f'/tasks/{task.pk}/'}


def project_data(project):
    return {'id': project.pk, 'name': project.name, 'description': project.description,
            'created_at': project.created_at.isoformat(),
            'task_count': getattr(project, 'task_count', project.tasks.count()),
            'done_count': getattr(project, 'done_count', project.tasks.filter(status=Task.Status.DONE).count()),
            'label_count': getattr(project, 'label_count', project.tasks.values('labels').distinct().count())}


def label_data(label):
    return {'id': label.pk, 'name': label.name, 'color': label.color,
            'created_at': label.created_at.isoformat(),
            'task_count': getattr(label, 'task_count', label.tasks.count())}


@endpoint(['GET'])
def csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


@endpoint(['POST'], fields=('username', 'email', 'password1', 'password2', 'terms'))
def register(request):
    if request.user.is_authenticated:
        return error('already_authenticated', 'Log out before creating another account.', 409)
    form = RegisterForm(request.api_data)
    if not form.is_valid():
        return invalid(form)
    try:
        with transaction.atomic():
            user = form.save()
    except IntegrityError:
        if not get_user_model().objects.filter(username=form.cleaned_data['username']).exists():
            raise
        form.add_error('username', 'A user with this username already exists.')
        return invalid(form, 409)
    login(request, user)
    return JsonResponse({'user': user_data(user), 'csrfToken': get_token(request),
                         'redirect_url': '/tasks/', 'message': 'Account created. Welcome!'}, status=201)


@endpoint(['POST'], fields=('username', 'password', 'next'))
def sign_in(request):
    form = LoginForm(request=request, data=request.api_data)
    if not form.is_valid():
        return invalid(form, 401 if form.non_field_errors() else 400)
    login(request, form.get_user())
    target = request.api_data.get('next', '')
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = '/tasks/'
    return JsonResponse({'user': user_data(request.user), 'csrfToken': get_token(request),
                         'redirect_url': target, 'message': 'Logged in successfully.'})


@endpoint(['POST'], private=True)
def sign_out(request):
    logout(request)
    return JsonResponse({'message': 'Logged out.', 'redirect_url': '/'})


@endpoint(['GET'], private=True)
def me(request):
    return JsonResponse({'user': user_data(request.user)})


@endpoint(['GET'], private=True)
def options(request):
    return JsonResponse({'statuses': [{'value': v, 'label': l} for v, l in Task.Status.choices],
                         'priorities': [{'value': v, 'label': l} for v, l in Task.Priority.choices]})


TASK_FIELDS = ('title', 'description', 'status', 'priority', 'due_date', 'project_id', 'label_ids')


def save_task(request, task=None):
    data = request.api_data.copy()
    if request.method == 'PATCH':
        original = task_data(task)
        data = {name: data.get(name, original[name]) for name in TASK_FIELDS}
    form_data = {name: value for name, value in data.items() if name not in ('project_id', 'label_ids')}
    form_data['project'] = data.get('project_id') or ''
    form_data['labels'] = data.get('label_ids', [])
    form = TaskForm(form_data, instance=task, owner=request.user)
    if not form.is_valid():
        return invalid(form)
    saved = form.save(commit=False)
    saved.owner = request.user
    saved.save()
    form.save_m2m()
    return JsonResponse({'task': task_data(saved), 'redirect_url': f'/tasks/{saved.pk}/',
                         'message': 'Task saved.' if task else 'Task created.'}, status=200 if task else 201)


@endpoint(['GET', 'POST'], private=True, fields=TASK_FIELDS)
def tasks(request):
    if request.method == 'POST':
        return save_task(request)
    all_tasks = Task.objects.filter(owner=request.user)
    result = all_tasks.select_related('project').prefetch_related('labels')
    fields = {}
    for name, choices in (('status', Task.Status.values), ('priority', Task.Priority.values)):
        value = request.GET.get(name, '')
        if value:
            if value not in choices:
                fields[name] = ['Invalid choice.']
            else:
                result = result.filter(**{name: value})
    query = request.GET.get('q', '').strip()
    if query:
        result = result.filter(Q(title__icontains=query) | Q(description__icontains=query))
    for name, relation in (('project_id', 'project_id'), ('label_id', 'labels__id')):
        value = request.GET.get(name, '')
        if value:
            if not value.isdigit():
                fields[name] = ['Use an integer.']
            else:
                result = result.filter(**{relation: value})
    has_project = request.GET.get('has_project', '')
    if has_project:
        if has_project not in ('true', 'false'):
            fields['has_project'] = ['Use true or false.']
        else:
            result = result.filter(project__isnull=has_project == 'false')
    ordering = {'newest': ('-created_at', '-pk'), 'oldest': ('created_at', 'pk'), 'title': ('title', 'pk')}
    sort = request.GET.get('sort', 'newest')
    if sort not in ordering:
        fields['sort'] = ['Invalid sort order.']
    try:
        page_number = int(request.GET.get('page', '1'))
        page_size = int(request.GET.get('page_size', '6'))
        if page_number < 1 or not 1 <= page_size <= 100:
            raise ValueError
    except ValueError:
        fields['page'] = ['Use a positive page and a page_size between 1 and 100.']
    if fields:
        return error('validation_error', 'Invalid query parameters.', fields=fields)
    paginator = Paginator(result.distinct().order_by(*ordering[sort]), page_size)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        return error('not_found', 'Page not found.', 404)
    return JsonResponse({'results': [task_data(task) for task in page], 'count': paginator.count,
                         'page': page.number, 'page_size': page_size, 'pages': paginator.num_pages,
                         'next': page.next_page_number() if page.has_next() else None,
                         'previous': page.previous_page_number() if page.has_previous() else None,
                         'stats': {'total': all_tasks.count(), 'active': all_tasks.exclude(status='done').count(),
                                   'done': all_tasks.filter(status='done').count()}})


@endpoint(['GET', 'PUT', 'PATCH', 'DELETE'], private=True, fields=TASK_FIELDS)
def task_detail(request, pk):
    task = Task.objects.select_related('project').prefetch_related('labels').filter(pk=pk, owner=request.user).first()
    if task is None:
        return error('not_found', 'Task not found.', 404)
    if request.method == 'GET':
        return JsonResponse({'task': task_data(task)})
    if request.method == 'DELETE':
        task.delete()
        return HttpResponse(status=204)
    return save_task(request, task)


def project_queryset(user):
    return Project.objects.filter(owner=user).annotate(
        task_count=Count('tasks', distinct=True),
        done_count=Count('tasks', filter=Q(tasks__status=Task.Status.DONE), distinct=True),
        label_count=Count('tasks__labels', distinct=True),
    )


@endpoint(['GET', 'POST'], private=True, fields=('name', 'description'))
def projects(request):
    if request.method == 'GET':
        return JsonResponse({'results': [project_data(item) for item in project_queryset(request.user)]})
    form = ProjectForm(request.api_data, owner=request.user)
    if not form.is_valid():
        return invalid(form)
    item = form.save()
    item.task_count = item.done_count = item.label_count = 0
    return JsonResponse({'project': project_data(item), 'message': 'Project created.'}, status=201)


@endpoint(['GET', 'PUT', 'PATCH', 'DELETE'], private=True, fields=('name', 'description'))
def project_detail(request, pk):
    project = project_queryset(request.user).filter(pk=pk).first()
    if project is None:
        return error('not_found', 'Project not found.', 404)
    if request.method == 'GET':
        tasks = Task.objects.filter(project=project).select_related('project').prefetch_related('labels')
        return JsonResponse({'project': project_data(project), 'tasks': [task_data(item) for item in tasks]})
    if request.method == 'DELETE':
        project.delete()
        return HttpResponse(status=204)
    data = request.api_data.copy()
    if request.method == 'PATCH':
        data = {'name': data.get('name', project.name), 'description': data.get('description', project.description)}
    form = ProjectForm(data, instance=project, owner=request.user)
    if not form.is_valid():
        return invalid(form)
    item = form.save()
    item.task_count, item.done_count, item.label_count = project.task_count, project.done_count, project.label_count
    return JsonResponse({'project': project_data(item), 'message': 'Project saved.'})


def label_queryset(user):
    return Label.objects.filter(owner=user).annotate(task_count=Count('tasks', distinct=True))


@endpoint(['GET', 'POST'], private=True, fields=('name', 'color'))
def labels(request):
    if request.method == 'GET':
        return JsonResponse({'results': [label_data(item) for item in label_queryset(request.user)]})
    form = LabelForm(request.api_data, owner=request.user)
    if not form.is_valid():
        return invalid(form)
    item = form.save()
    item.task_count = 0
    return JsonResponse({'label': label_data(item), 'message': 'Label created.'}, status=201)


@endpoint(['GET', 'PATCH', 'DELETE'], private=True, fields=('name', 'color'))
def label_detail(request, pk):
    label = label_queryset(request.user).filter(pk=pk).first()
    if label is None:
        return error('not_found', 'Label not found.', 404)
    if request.method == 'GET':
        return JsonResponse({'label': label_data(label)})
    if request.method == 'DELETE':
        label.delete()
        return HttpResponse(status=204)
    data = {'name': request.api_data.get('name', label.name), 'color': request.api_data.get('color', label.color)}
    form = LabelForm(data, instance=label, owner=request.user)
    if not form.is_valid():
        return invalid(form)
    item = form.save()
    item.task_count = label.task_count
    return JsonResponse({'label': label_data(item), 'message': 'Label saved.'})


@endpoint(['GET'], private=True)
def project_report(request):
    projects = project_queryset(request.user)
    labels = label_queryset(request.user)
    return JsonResponse({
        'projects': [project_data(item) for item in projects],
        'labels': [label_data(item) for item in labels],
        'unassigned_tasks': Task.objects.filter(owner=request.user, project=None).count(),
        'matrix': [
            {'project_id': project.pk, 'project': project.name, 'label_id': label.pk, 'label': label.name,
             'task_count': Task.objects.filter(owner=request.user, project=project, labels=label).count()}
            for project in projects for label in labels
        ],
    })


def not_found(request, **kwargs):
    return error('not_found', 'API endpoint not found.', 404)
