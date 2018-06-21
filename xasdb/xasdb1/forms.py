from django.forms import (Form, FileField, ModelForm, CharField, EmailField)
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import XASFile

class FormWithFileField(Form):
    download_file = FileField()

class ModelFormWithFileField(ModelForm):
    class Meta:
        model = XASFile
        fields = ['upload_file']

class XASDBUserCreationForm(UserCreationForm):
    first_name = CharField(max_length=100, min_length=1)
    last_name = CharField(max_length=100, min_length=1)
    email = EmailField(max_length=100)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
