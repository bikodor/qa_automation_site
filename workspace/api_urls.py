from django.urls import path, re_path
from . import api

urlpatterns = [
    path('auth/csrf/', api.csrf),
    path('auth/register/', api.register),
    path('auth/login/', api.sign_in),
    path('auth/logout/', api.sign_out),
    path('auth/me/', api.me),
    path('tasks/options/', api.options),
    path('tasks/', api.tasks),
    path('tasks/<int:pk>/', api.task_detail),
    path('projects/', api.projects),
    path('projects/<int:pk>/', api.project_detail),
    path('labels/', api.labels),
    path('labels/<int:pk>/', api.label_detail),
    path('reports/project-summary/', api.project_report),
    re_path(r'^.*$', api.not_found),
]
