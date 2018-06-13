from django.shortcuts import (render, redirect)
from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm

from django.contrib.auth import authenticate
from django.contrib.auth import login as _login
from django.contrib.auth import logout as _logout

from .forms import FormWithFileField, ModelFormWithFileField
from .models import XASFile

import xdifile
import xraylib as xrl
import tempfile
import json
import numpy as np
import io
import matplotlib.pyplot as plt

def index(request):
    return render(request, 'xasdb1/index.html')

def register(request):
    if request.method == 'POST':
        f = UserCreationForm(request.POST)
        if f.is_valid():
            f.save()
            messages.success(request, 'Account created successfully')
            return redirect('/xasdb1/register')

    else:
        f = UserCreationForm()

    return render(request, 'xasdb1/register.html', {'form': f})

class AuthenticationFormWithInactiveUsersOkay(AuthenticationForm):
    def confirm_login_allowed(self, user):
        pass

def login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/xasdb1/')
    if request.method == 'POST':
        f = AuthenticationFormWithInactiveUsersOkay(request, data=request.POST)
        if f.is_valid():
            username = f.cleaned_data.get('username')
            password = f.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                print(user)
                _login(request, user)
                messages.success(request, username + ' logged in!')
                return HttpResponseRedirect('/xasdb1/')
            else:
                print('User not found')
            messages.error(request, 'Could not authenticate ' + username)
            return redirect('login')

    else:
        f = AuthenticationFormWithInactiveUsersOkay()

    return render(request, 'xasdb1/login.html', {'form': f})
    
def logout(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Not logged in!')
        return HttpResponseRedirect('/xasdb1/')
    _logout(request)
    messages.success(request, 'Logged out!')
    return HttpResponseRedirect('/xasdb1/')

def element(request, element_id):
    # user may be naughty by providing a non-existent element
    if xrl.SymbolToAtomicNumber(element_id) == 0:
        messages.error(request, 'I am sure you already know that there is no element called ' + element_id + ' . Use the periodic table and stop fooling around.')
        return HttpResponseRedirect('/xasdb1/')
    # make a distinction between staff and non-staff:
    # 1. staff should be able to see all spectra, regardless of review_status, and should be able to change that review_status
    # 2. non-staff should be able to see all APPROVED spectra, as well as those uploaded by the user that were either rejected or pending review
    return render(request, 'xasdb1/element.html', {'element': element_id, 'files': XASFile.objects.filter(element=element_id).filter(review_status=XASFile.APPROVED).order_by('sample_name')})

@login_required
def upload(request):
    if request.method == 'POST':
        form = ModelFormWithFileField(request.POST, request.FILES)
        print('before form is_valid')
        if form.is_valid():
            print('before form save')
            value = request.FILES['upload_file']
            value.seek(0)
            with tempfile.NamedTemporaryFile() as f:
                contents = value.read()
                f.write(contents)
                xdi_file = xdifile.XDIFile(filename=f.name)
                value.seek(0)
            element = xdi_file.element.decode('utf-8')
            print('element: {}'.format(element))
            atomic_number = xrl.SymbolToAtomicNumber(element)
            print('atomic_number: {}'.format(atomic_number))
            edge = xdi_file.edge.decode('utf-8')
            print('edge: {}'.format(edge))
            kwargs = dict()
            if 'sample' in xdi_file.attrs and 'name' in xdi_file.attrs['sample']:
                kwargs['sample_name'] = xdi_file.attrs['sample']['name']
                print('sample_name: {}'.format(kwargs['sample_name']))

            xas_file = XASFile(atomic_number=atomic_number, upload_file=value, uploader=request.user, element=element, edge=edge, **kwargs)
            #form = ModelFormWithFileField(request.POST, instance = instance)
            try:
                xas_file.save()
                # add arrays
                for name, unit in zip(xdi_file.array_labels, xdi_file.array_units):
                    xas_file.xasarray_set.create(name=name, unit=unit, array=json.dumps(getattr(xdi_file, name).tolist()))
            except Exception as e:
                print('form.save() exception: {}'.format(e))
                #print('form.errors: {}'.format(form.errors))
            print('after form save')
            messages.success(request, 'File uploaded')
            return HttpResponseRedirect('/xasdb1/')
    else:
        form = ModelFormWithFileField()
    return render(request, 'xasdb1/upload.html', {'form': form})

def file(request, file_id):
    return render(request, 'xasdb1/file.html', {'file' : XASFile.objects.get(id=file_id)})

def file_plot(request, file_id, xaxis_name, yaxis_name):
    file = XASFile.objects.get(id=file_id)
    xaxis = np.array(json.loads(file.xasarray_set.get(name = xaxis_name).array))
    yaxis = np.array(json.loads(file.xasarray_set.get(name = yaxis_name).array))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlabel(xaxis_name) # TODO: unit
    ax.set_ylabel(yaxis_name)
    ax.plot(xaxis, yaxis)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    plt_bytes = buf.getvalue()
    buf.close()
    return HttpResponse(plt_bytes, content_type="image/png")

