from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import RegisterForm, TaskForm
from .models import Task


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
    tasks = all_tasks
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    sort = request.GET.get('sort', 'newest')
    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if status in Task.Status.values:
        tasks = tasks.filter(status=status)
    if priority in Task.Priority.values:
        tasks = tasks.filter(priority=priority)
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
        'priority': priority, 'sort': sort, 'statuses': Task.Status.choices,
        'priorities': Task.Priority.choices, 'params': params.urlencode(),
    })


@login_required
def task_form(request, pk=None):
    task = get_object_or_404(Task, pk=pk, owner=request.user) if pk else None
    form = TaskForm(request.POST if request.method == 'POST' else None, instance=task)
    if request.method == 'POST' and form.is_valid():
        task = form.save(commit=False)
        task.owner = request.user
        task.save()
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
