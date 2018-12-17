from django.forms import (Form, FileField, ModelForm, CharField, EmailField, TextInput, BaseModelFormSet, modelformset_factory, inlineformset_factory, BaseInlineFormSet)
from django.forms.widgets import FileInput
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import XASFile, XASUploadAuxData

class XASFileSubmissionForm(ModelForm):
    class Meta:
        model = XASFile
        fields = ['upload_file', 'upload_file_doi']
        widgets = {
                "upload_file_doi": TextInput(attrs={'onkeyup': "getDOI(this.value)"})
        }

class XASFileVerificationForm(ModelForm):
    class Meta:
        model = XASFile
        fields = ['review_status', 'upload_file_doi', 'element', 'edge', 'sample_name', 'sample_prep', 'beamline_name', 'facility_name', 'mono_name', 'mono_d_spacing']


class XASUploadAuxDataForm(ModelForm):
    class Meta:
        model = XASUploadAuxData
        fields = ('aux_description', 'aux_file')
        widgets = {'aux_file': FileInput(attrs={'class': 'aux_file_class'})} # I do not like the default ClearableFileInput form widget


class XASUploadAuxDataBaseFormSet(BaseModelFormSet):
    def clean(self):
        super().clean()
        descriptions = []
        files = []

        # ensure descriptions are unique!
        for index, form in enumerate(self.forms):
            #print(f'{index}')
            if form.cleaned_data:
                #print('cleaned_data found: {}'.format(', '.join(form.cleaned_data.keys())))
                # scenarios:
                # 1. aux_description and aux_file are both empty -> ignore this one and move on the next
                # 2. aux_description is empty but aux_file is not (and vice-versa) -> throw an error
                # 3. both fields are not empty -> ok (but ensure they are unique in the formset!)
                description = form.cleaned_data['aux_description']
                try:
                    file = form.cleaned_data['aux_file'].name # aux_file is an InMemoryUploadedFile instance, so we use the name to get the filename str (basename only)
                except:
                    file = None
                #print(f'x{description}x')
                #print(f'x{file}x')
                if description and file:
                    if description in descriptions:
                        raise ValidationError('Auxiliary data must contain unique descriptions')
                    elif file in files:
                        raise ValidationError('Auxiliary data must contain unique filenames')
                    descriptions.append(description)
                    files.append(file)
                elif description or file:
                    #print('raising ValidationError 2')
                    if not description:
                        form.add_error('aux_description', 'Unique description required')
                    elif not file:
                        form.add_error('aux_file', 'Unique filename required')
                    raise ValidationError('Valid auxiliary data consists of a unique description and a unique filename')

class XASUploadAuxDataBaseVerificationFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # need to ensure all descriptions are unique!
        descriptions = []

        for index, form in enumerate(self.forms):
            #print(f'{index}')
            if form.cleaned_data:
                description = form.cleaned_data['aux_description']
                #print(f'x{description}x')
                #print(f'x{file}x')
                if description:
                    if description in descriptions:
                        raise ValidationError('Auxiliary data must contain unique descriptions')
                    descriptions.append(description)
                else:
                    form.add_error('aux_description', 'Unique description required')
                    raise ValidationError('Valid auxiliary data consists of a unique description and a unique filename')

XASUploadAuxDataFormSet = modelformset_factory(XASUploadAuxData, form=XASUploadAuxDataForm, formset=XASUploadAuxDataBaseFormSet, max_num=10, extra=1, validate_max=True)

XASUploadAuxDataVerificationFormSet = inlineformset_factory(XASFile, XASUploadAuxData, formset=XASUploadAuxDataBaseVerificationFormSet, fields=('aux_description', ), extra=0, max_num=10, validate_max=True)

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
