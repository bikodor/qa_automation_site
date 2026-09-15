from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from workspace.models import Task


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
        if Task.objects.filter(owner=user).exists():
            self.stdout.write('Demo tasks already exist. Use --reset to replace them.')
            return
        titles = ['Gather requirements', 'Prepare test data', 'Check registration form',
                  'Set up the environment', 'Check task search', 'Update project description',
                  'Run the deletion scenario', 'Check the mobile layout', 'Explore boundary values',
                  'Check filters', 'Plan the week', 'Finish the first stage']
        for index, title in enumerate(titles):
            Task.objects.create(owner=user, title=title, description=f'Training task {index + 1}. Add notes and verify that changes are saved.',
                                status=Task.Status.values[index % 3], priority=Task.Priority.values[(index // 3) % 3],
                                due_date=date(2026, 9, 15) + timedelta(days=index) if index % 4 else None)
        self.stdout.write(self.style.SUCCESS('Demo ready: demo / DemoPass123! (12 tasks)'))
