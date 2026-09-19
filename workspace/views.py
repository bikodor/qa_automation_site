from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import LabelForm, ProjectForm, RegisterForm, TaskForm
from .models import Label, Project, Task


def home(request):
    return render(request, 'home.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('tasks')
    form = RegisterForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            # A second request may create the same username after form validation.
            # Keep this a normal validation response instead of exposing a 500 page.
            form.add_error('username', 'A user with this username already exists.')
            return render(request, 'form.html', {'form': form, 'title': 'Create an account', 'subtitle': 'Your private task workspace.', 'submit': 'Create account', 'kind': 'register'})
        login(request, user)
        messages.success(request, 'Account created. Welcome!')
        return redirect('tasks')
    return render(request, 'form.html', {'form': form, 'title': 'Create an account', 'subtitle': 'Your private task workspace.', 'submit': 'Create account', 'kind': 'register'})


@login_required
def task_list(request):
    all_tasks = Task.objects.filter(owner=request.user)
    tasks = all_tasks.select_related('project').prefetch_related('labels')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    project_id = request.GET.get('project_id', '')
    label_id = request.GET.get('label_id', '')
    sort = request.GET.get('sort', 'newest')
    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if status in Task.Status.values:
        tasks = tasks.filter(status=status)
    if priority in Task.Priority.values:
        tasks = tasks.filter(priority=priority)
    if project_id.isdigit():
        tasks = tasks.filter(project_id=project_id, project__owner=request.user)
    if label_id.isdigit():
        tasks = tasks.filter(labels__id=label_id, labels__owner=request.user).distinct()
    ordering = {'newest': ('-created_at', '-pk'), 'oldest': ('created_at', 'pk'), 'title': ('title', 'pk')}
    if sort not in ordering:
        sort = 'newest'
    tasks = tasks.order_by(*ordering[sort])
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'tasks.html', {
        'page_obj': Paginator(tasks, 6).get_page(request.GET.get('page')),
        'total': all_tasks.count(), 'active': all_tasks.exclude(status='done').count(),
        'done': all_tasks.filter(status='done').count(), 'q': query, 'status': status,
        'priority': priority, 'project_id': project_id, 'label_id': label_id, 'sort': sort,
        'projects': Project.objects.filter(owner=request.user), 'labels': Label.objects.filter(owner=request.user),
        'statuses': Task.Status.choices,
        'priorities': Task.Priority.choices, 'params': params.urlencode(),
    })


@login_required
def task_form(request, pk=None):
    task = get_object_or_404(Task, pk=pk, owner=request.user) if pk else None
    form = TaskForm(request.POST if request.method == 'POST' else None, instance=task, owner=request.user)
    if request.method == 'POST' and form.is_valid():
        task = form.save(commit=False)
        task.owner = request.user
        task.save()
        form.save_m2m()
        messages.success(request, 'Task saved.' if pk else 'Task created.')
        return redirect('task-detail', pk=task.pk)
    return render(request, 'form.html', {'form': form, 'title': 'Edit task' if pk else 'New task', 'subtitle': 'Define the next step.', 'submit': 'Save', 'kind': 'task'})


@login_required
def task_detail(request, pk):
    return render(request, 'detail.html', {'task': get_object_or_404(Task, pk=pk, owner=request.user)})


@login_required
@require_POST
def task_delete(request, pk):
    get_object_or_404(Task, pk=pk, owner=request.user).delete()
    messages.success(request, 'Task deleted.')
    return redirect('tasks')


@login_required
def project_workspace(request):
    action = request.POST.get('action') if request.method == 'POST' else None
    project_form = ProjectForm(request.POST if action == 'project' else None, owner=request.user)
    label_form = LabelForm(request.POST if action == 'label' else None, owner=request.user)
    if request.method == 'POST':
        form = project_form if action == 'project' else label_form
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            messages.success(request, 'Project created.' if action == 'project' else 'Label created.')
            return redirect('projects')
    projects = Project.objects.filter(owner=request.user).annotate(
        task_count=Count('tasks', distinct=True),
        done_count=Count('tasks', filter=Q(tasks__status=Task.Status.DONE), distinct=True),
        label_count=Count('tasks__labels', distinct=True),
    )
    labels = Label.objects.filter(owner=request.user).annotate(task_count=Count('tasks', distinct=True))
    return render(request, 'projects.html', {
        'projects': projects, 'labels': labels,
        'project_form': project_form, 'label_form': label_form,
        'unassigned_count': Task.objects.filter(owner=request.user, project=None).count(),
    })


@login_required
@require_POST
def project_delete(request, pk):
    get_object_or_404(Project, pk=pk, owner=request.user).delete()
    messages.success(request, 'Project deleted. Its tasks are now unassigned.')
    return redirect('projects')


@login_required
@require_POST
def label_delete(request, pk):
    get_object_or_404(Label, pk=pk, owner=request.user).delete()
    messages.success(request, 'Label deleted.')
    return redirect('projects')
