from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Label, Project, Task


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
    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.filter(owner=owner) if owner else Project.objects.none()
        self.fields['labels'].queryset = Label.objects.filter(owner=owner) if owner else Label.objects.none()

    class Meta:
        model = Task
        fields = ['title', 'description', 'project', 'labels', 'status', 'priority', 'due_date']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'due_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }


class ProjectForm(TestableFormMixin, forms.ModelForm):
    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner:
            self.instance.owner = owner

    def clean_name(self):
        name = self.cleaned_data['name']
        duplicate = Project.objects.filter(owner=self.instance.owner, name=name).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError('You already have a project with this name.')
        return name

    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class LabelForm(TestableFormMixin, forms.ModelForm):
    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner:
            self.instance.owner = owner

    def clean_name(self):
        name = self.cleaned_data['name']
        duplicate = Label.objects.filter(owner=self.instance.owner, name=name).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError('You already have a label with this name.')
        return name

    class Meta:
        model = Label
        fields = ['name', 'color']
