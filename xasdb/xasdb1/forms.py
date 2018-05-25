from django.forms import (Form, FileField, ModelForm)
from .models import XASFile

class FormWithFileField(Form):
    download_file = FileField()

class ModelFormWithFileField(ModelForm):
    class Meta:
        model = XASFile
        fields = ['upload_file']
