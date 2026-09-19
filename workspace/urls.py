from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from . import views
from .forms import LoginForm

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', LoginView.as_view(template_name='form.html', authentication_form=LoginForm, extra_context={'title': 'Welcome back', 'subtitle': 'Log in to continue working.', 'submit': 'Log in', 'kind': 'login'}), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('tasks/', views.task_list, name='tasks'),
    path('tasks/new/', views.task_form, name='task-create'),
    path('tasks/<int:pk>/', views.task_detail, name='task-detail'),
    path('tasks/<int:pk>/edit/', views.task_form, name='task-edit'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task-delete'),
    path('projects/', views.project_workspace, name='projects'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project-delete'),
    path('labels/<int:pk>/delete/', views.label_delete, name='label-delete'),
]
