from django.shortcuts import (render, redirect)
from django.http import HttpResponse
from django.urls import reverse

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm

from django.contrib.auth import authenticate
from django.contrib.auth import login as _login
from django.contrib.auth import logout as _logout

from django.db.models import Q

from .forms import FormWithFileField, ModelFormWithFileField
from .models import XASFile, XASMode, XASArray
from .utils import process_xdi_file

import xraylib as xrl
import tempfile
import json
import numpy as np
import io
import matplotlib
matplotlib.use('Agg', warn=False) # avoid Travis-CI DISPLAY exception when using default Qt5 backend
import matplotlib.pyplot as plt
import os.path
import base64

XDI_TMP_DIR = tempfile.TemporaryDirectory()

def index(request):
    return render(request, 'xasdb1/index.html')

def register(request):
    if request.method == 'POST':
        f = UserCreationForm(request.POST)
        if f.is_valid():
            f.save()
            messages.success(request, 'Account created successfully')
            return redirect('xasdb1:index')
    else:
        f = UserCreationForm()

    return render(request, 'xasdb1/register.html', {'form': f})

class AuthenticationFormWithInactiveUsersOkay(AuthenticationForm):
    def confirm_login_allowed(self, user):
        pass

def login(request):
    if request.user.is_authenticated:
        return redirect('xasdb1:index')
    if request.method == 'POST':
        f = AuthenticationFormWithInactiveUsersOkay(request, data=request.POST)
        if f.is_valid():
            username = f.cleaned_data.get('username')
            password = f.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                _login(request, user)
                messages.success(request, username + ' logged in!')
                return redirect('xasdb1:index')
            messages.error(request, 'Could not authenticate ' + username)
        #else:
        #    return
        #    print('Invalid form -> probably means that the username or password is incorrect!')
    else:
        f = AuthenticationFormWithInactiveUsersOkay()

    return render(request, 'xasdb1/login.html', {'form': f})
    
def logout(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Not logged in!')
        return redirect('xasdb1:index')
    _logout(request)
    messages.success(request, 'Logged out!')
    return redirect('xasdb1:index')

def element(request, element_id):
    # user may be naughty by providing a non-existent element
    if xrl.SymbolToAtomicNumber(element_id) == 0:
        messages.error(request, 'I am sure you already know that there is no element called ' + element_id + ' . Use the periodic table and stop fooling around.')
        return redirect('xasdb1:index')
    # make a distinction between staff and non-staff:
    # 1. staff should be able to see all spectra, regardless of review_status, and should be able to change that review_status
    if request.user.is_staff:
        return render(request, 'xasdb1/element.html', {'element': element_id, 'files': XASFile.objects.filter(element=element_id).order_by('sample_name')})
    # 2. non-staff should be able to see all APPROVED spectra, as well as those uploaded by the user that were either rejected or pending review
    elif request.user.is_authenticated:
        data_filter = Q(uploader=request.user) | (~Q(uploader=request.user) & Q(review_status=XASFile.APPROVED))
        return render(request, 'xasdb1/element.html', {'element': element_id, 'files': XASFile.objects.filter(element=element_id).filter(data_filter).order_by('sample_name')})
    else:
        return render(request, 'xasdb1/element.html', {'element': element_id, 'files': XASFile.objects.filter(element=element_id).filter(review_status=XASFile.APPROVED).order_by('sample_name')})

@login_required(login_url='xasdb1:login')
def upload(request):
    if request.method == 'POST':
        form = ModelFormWithFileField(request.POST, request.FILES)
        if form.is_valid():
            value = request.FILES['upload_file']
            value.seek(0)
            temp_xdi_file = os.path.join(XDI_TMP_DIR.name, value.name)
            with open(temp_xdi_file, 'w') as f:
                contents = value.read().decode('utf-8')
                f.write(contents)
            process_xdi_file(temp_xdi_file, request)
            messages.success(request, 'File uploaded')
            return redirect('xasdb1:index')
    else:
        form = ModelFormWithFileField()
    return render(request, 'xasdb1/upload.html', {'form': form})

def file(request, file_id):
    # check first if this should be visible for the current user
    file = XASFile.objects.get(id=file_id)
    #print(f'request.user: {request.user}')
    #print(f'request.user.is_authenticated: {request.user.is_authenticated}')
    #print(f'request.user.is_staff: {request.user.is_staff}')
    #print(f'file.uploader: {file.uploader}')
    #print(f'file.review_status: {file.review_status}')
    if (not request.user.is_authenticated and file.review_status != XASFile.APPROVED) or (not request.user.is_staff and request.user != file.uploader and file.review_status != XASFile.APPROVED):
        messages.error(request, 'The requested file is not accessible')
        return redirect('xasdb1:index')


    # get modes
    file = XASFile.objects.get(id=file_id)
    modes = file.xasmode_set.all()
    plots = []

    if len(modes) == 0:
        messages.error(request, 'No modes found')
    else:
        if len(modes) > 1:
            print('Warning: more than one mode detected. Using first mode!')
        mode = modes[0].mode
        if mode == XASMode.TRANSMISSION:
            try:
                energy = np.array(json.loads(file.xasarray_set.get(name='energy').array))
                i0 = np.array(json.loads(file.xasarray_set.get(name='i0').array))
                itrans = np.array(json.loads(file.xasarray_set.get(name='itrans').array))
                mutrans = -np.log(itrans/i0)
            except Exception as e:
                messages.error(request, 'Could not extract data from transmission spectrum: ' + str(e))
        else: # assume fluorescence for now...
            try:
                energy = np.array(json.loads(file.xasarray_set.get(name='energy').array))
                i0 = np.array(json.loads(file.xasarray_set.get(name='i0').array))
                ifluor = np.array(json.loads(file.xasarray_set.get(name='ifluor').array))
                mutrans = ifluor/i0
            except Exception as e:
                messages.error(request, 'Could not extract data from fluorescence spectrum: ' + str(e))

        if len(messages.get_messages(request)) == 0:
            murefer = None
            try:
                irefer = np.array(json.loads(file.xasarray_set.get(name='irefer').array))
                murefer = -np.log(irefer/itrans)
            except:
                pass
            plots.append(_file_plot(energy, mutrans, "Energy (eV)", "Raw XAFS"))

    return render(request, 'xasdb1/file.html', {'file' : file, 'plots': plots})
    

def _file_plot(xaxis, yaxis, xaxis_name, yaxis_name):
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
    return str(base64.b64encode(plt_bytes), encoding='utf-8')

