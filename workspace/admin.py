from django.contrib import admin
from .models import Label, Project, Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'project', 'status', 'priority', 'due_date']
    list_filter = ['project', 'labels', 'status', 'priority']
    search_fields = ['title', 'description']
    filter_horizontal = ['labels']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at']
    search_fields = ['name', 'description', 'owner__username']


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'owner', 'created_at']
    list_filter = ['color']
    search_fields = ['name', 'owner__username']
