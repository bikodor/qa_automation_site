from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from workspace.models import Label, Project, Task


class Command(BaseCommand):
    help = 'Create demo / DemoPass123! and sample tasks. --reset replaces only demo tasks and password.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        user, created = get_user_model().objects.get_or_create(username='demo', defaults={'email': 'demo@example.com'})
        if created or options['reset']:
            user.set_password('DemoPass123!')
            user.save()
        if options['reset']:
            Task.objects.filter(owner=user).delete()
            Project.objects.filter(owner=user).delete()
            Label.objects.filter(owner=user).delete()
        projects = [Project.objects.get_or_create(owner=user, name=name, defaults={'description': description})[0]
                    for name, description in (
                        ('Web application', 'Browser flows, forms and responsive behavior.'),
                        ('Public API', 'JSON contracts, auth and validation scenarios.'),
                        ('Release 1.0', 'Regression scope for the first release.'),
                    )]
        labels = [Label.objects.get_or_create(owner=user, name=name, defaults={'color': color})[0]
                  for name, color in (('API', 'blue'), ('UI', 'purple'), ('Regression', 'green'),
                                      ('Critical', 'red'), ('Data', 'amber'))]
        titles = ['Gather requirements', 'Prepare test data', 'Check registration form',
                  'Set up the environment', 'Check task search', 'Update project description',
                  'Run the deletion scenario', 'Check the mobile layout', 'Explore boundary values',
                  'Check filters', 'Plan the week', 'Finish the first stage']
        tasks = list(Task.objects.filter(owner=user).order_by('pk'))
        if not tasks:
            for index, title in enumerate(titles):
                tasks.append(Task.objects.create(
                    owner=user, title=title,
                    description=f'Training task {index + 1}. Add notes and verify that changes are saved.',
                    status=Task.Status.values[index % 3], priority=Task.Priority.values[(index // 3) % 3],
                    due_date=date(2026, 9, 15) + timedelta(days=index) if index % 4 else None,
                ))
        for index, task in enumerate(tasks):
            task.project = None if index % 5 == 0 else projects[index % len(projects)]
            task.save(update_fields=['project'])
            task.labels.set([labels[index % len(labels)], labels[(index + 2) % len(labels)]])
        self.stdout.write(self.style.SUCCESS(
            f'Demo ready: demo / DemoPass123! ({len(tasks)} tasks, 3 projects, 5 labels)'))
