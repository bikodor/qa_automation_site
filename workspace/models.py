from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = 'todo', 'To do'
        IN_PROGRESS = 'in_progress', 'In progress'
        DONE = 'done', 'Done'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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
