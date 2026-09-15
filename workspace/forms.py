from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Task


class TestableFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['data-testid'] = name


class LoginForm(TestableFormMixin, AuthenticationForm):
    pass


class RegisterForm(TestableFormMixin, UserCreationForm):
    email = forms.EmailField(label='Email', required=True)
    terms = forms.BooleanField(label='I accept the training workspace terms')

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'terms']


class TaskForm(TestableFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'status', 'priority', 'due_date']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'due_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }
