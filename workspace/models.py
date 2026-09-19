from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models


class Project(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField('Name', max_length=80, validators=[MinLengthValidator(2)])
    description = models.TextField('Description', blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name', 'pk']
        constraints = [models.UniqueConstraint(fields=['owner', 'name'], name='unique_project_name_per_owner')]

    def __str__(self):
        return self.name


class Label(models.Model):
    class Color(models.TextChoices):
        BLUE = 'blue', 'Blue'
        GREEN = 'green', 'Green'
        AMBER = 'amber', 'Amber'
        RED = 'red', 'Red'
        PURPLE = 'purple', 'Purple'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='labels')
    name = models.CharField('Name', max_length=40, validators=[MinLengthValidator(2)])
    color = models.CharField('Color', max_length=10, choices=Color, default=Color.BLUE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name', 'pk']
        constraints = [models.UniqueConstraint(fields=['owner', 'name'], name='unique_label_name_per_owner')]

    def __str__(self):
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = 'todo', 'To do'
        IN_PROGRESS = 'in_progress', 'In progress'
        DONE = 'done', 'Done'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True, related_name='tasks')
    labels = models.ManyToManyField(Label, blank=True, related_name='tasks')
    title = models.CharField('Title', max_length=120, validators=[MinLengthValidator(3)])
    description = models.TextField('Description', blank=True, max_length=2000)
    status = models.CharField('Status', max_length=20, choices=Status, default=Status.TODO)
    priority = models.CharField('Priority', max_length=10, choices=Priority, default=Priority.MEDIUM)
    due_date = models.DateField('Due date', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return self.title
