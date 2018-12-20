from django.shortcuts import (render, redirect)
from django.http import HttpResponse, FileResponse
from django.urls import reverse

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site

from django.contrib.auth import authenticate
from django.contrib.auth import login as _login
from django.contrib.auth import logout as _logout

from django.conf import settings

from django.db.models import Q

from django.utils.encoding import force_bytes, force_text, smart_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from django.core.mail import mail_admins, send_mail

from .forms import XASFileSubmissionForm, XASDBUserCreationForm, XASUploadAuxDataFormSet, XASFileVerificationForm, XASUploadAuxDataVerificationFormSet
from .models import XASFile, XASMode, XASArray, XASUploadAuxData
from .utils import process_xdi_file
from .tokens import account_activation_token

import xraylib as xrl
import tempfile
import json
import numpy as np
import mimetypes

from bokeh.plotting import figure, output_file, show 
from bokeh.embed import components
from bokeh import __version__ as bokeh_version

import os.path
import base64
from habanero import Crossref
import traceback

HOST = 'https://xasdb.diamond.ac.uk'

XDI_TMP_DIR = tempfile.TemporaryDirectory()

OUR_CITATION = \
        '''<div style="padding-left:30px">G. Cibin, D. Gianolio, S. A. Parry, T. Schoonjans, O. Moore, R. Draper, L. A. Miller, A. Thoma, C. L. Doswell, and A. Graham. An open access, integrated XAS data repository at Diamond Light Source. <i>XAFS 2018 conference proceedings</i> (2019)</div>''' # add clickable doi url when known!

def index(request):
    return render(request, 'xasdb1/index.html')

def register(request):
    if request.method == 'POST':
        f = XASDBUserCreationForm(request.POST)
        if f.is_valid():
            user = f.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk)).decode()
            token = account_activation_token.make_token(user)
            message = 'Hi {user},\nPlease click on the link to confirm your registration,\n\n{domain}{url}'.format(
                user=user.get_full_name(),
                domain=HOST,
                url=reverse('xasdb1:activate', args=[uid, token])
            )
            send_mail('Activate your account', message, settings.SERVER_EMAIL, [user.email])
            mail_admins('a new user has registered', 'Name: {name}\nEmail: {email}\n\nAn activation email has been sent to the new user for confirmation'.format(name=user.get_full_name(), email=user.email))
            messages.success(request, 'Account created successfully: please activate using the email that was sent to you')
            return redirect('xasdb1:index')
    else:
        f = XASDBUserCreationForm()

    return render(request, 'xasdb1/register.html', {'form': f})

def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        # send email to admins
        messages.success(request, 'Your account has now been activated. Please login to start uploading and downloading datasets')
        return redirect('xasdb1:login')
    else:
        messages.error(request, 'Your activation request has been denied, probably because the link has expired. Please contact the admins to get a new one.')
        return redirect('xasdb1:index')


def login(request):
    if request.user.is_authenticated:
        return redirect('xasdb1:index')
    if request.method == 'POST':
        f = AuthenticationForm(request, data=request.POST)
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
        f = AuthenticationForm()

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
    elif request.user.is_staff:
        return render(request, 'xasdb1/element.html', {'element': element_id, 'files': XASFile.objects.filter(element=element_id).order_by('sample_name')})

    # 2. non-staff should be able to see all APPROVED spectra, as well as those uploaded by the user that were either rejected or pending review
    elif request.user.is_authenticated:
        data_filter = Q(uploader=request.user) | (~Q(uploader=request.user) & Q(review_status=XASFile.APPROVED))
        return render(request, 'xasdb1/element.html', {'element': element_id, 'files': XASFile.objects.filter(element=element_id).filter(data_filter).order_by('sample_name')})

    else:
        return render(request, 'xasdb1/element.html', {'element': element_id, 'files': XASFile.objects.filter(element=element_id).filter(review_status=XASFile.APPROVED).order_by('sample_name')})

@login_required(login_url='xasdb1:login')
def upload(request):
    #print(f"request.method: {request.method}")
    if request.method == 'POST':
        form = XASFileSubmissionForm(request.POST, request.FILES)
        upload_aux_formset = XASUploadAuxDataFormSet(request.POST, request.FILES)
        form_is_valid = form.is_valid()
        upload_aux_formset_is_valid = upload_aux_formset.is_valid()
        #print(f"form_is_valid: {form_is_valid}")
        #print(f"upload_aux_formset_is_valid: {upload_aux_formset_is_valid}")
        if form_is_valid and upload_aux_formset_is_valid:
            #print("upload::POST -> is_valid")
            value = request.FILES['upload_file']
            value.seek(0)
            temp_xdi_file = os.path.join(XDI_TMP_DIR.name, value.name)
            with open(temp_xdi_file, 'w') as f:
                contents = value.read().decode('utf-8')
                f.write(contents)
            xas_file = process_xdi_file(temp_xdi_file, request)
            # add auxiliary data
            for index, upload_aux_form in enumerate(upload_aux_formset):
                #print(f"index: {index}")
                try:
                    xas_file.xasuploadauxdata_set.create(aux_description=upload_aux_form.cleaned_data['aux_description'], aux_file=upload_aux_form.cleaned_data['aux_file'])
                except:
                    pass
            messages.success(request, 'File uploaded')

            new_redirect = redirect('xasdb1:file', xas_file.id)
            # send email to maintainers
            mail_admins( \
                'a new dataset has been uploaded', \
                'A new dataset has been uploaded by {} ({}).\nPlease process this submission by visiting {}.'.format(request.user.get_full_name(), request.user.email, HOST + new_redirect.url))


            return new_redirect
    else:
        form = XASFileSubmissionForm()
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '10',
            'form-MIN_NUM_FORMS': '0',
        }
        upload_aux_formset = XASUploadAuxDataFormSet(data, initial=[{'aux_description': "", 'aux_file': ""}])
    return render(request, 'xasdb1/upload.html', {'form': form, 'upload_aux_formset': upload_aux_formset})

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
        yaxis_title = "Raw XAFS"
        if mode == XASMode.TRANSMISSION:
            try:
                energy = np.array(json.loads(file.xasarray_set.get(name='energy').array))
                i0 = np.array(json.loads(file.xasarray_set.get(name='i0').array))
                itrans = np.array(json.loads(file.xasarray_set.get(name='itrans').array))
                mutrans = -np.log(itrans/i0)
            except Exception as e:
                messages.error(request, 'Could not extract data from transmission spectrum: ' + str(e))
        elif mode == XASMode.FLUORESCENCE or mode == XASMode.FLUORESCENCE_UNITSTEP:
            try:
                energy = np.array(json.loads(file.xasarray_set.get(name='energy').array))
                i0 = np.array(json.loads(file.xasarray_set.get(name='i0').array))
                ifluor = np.array(json.loads(file.xasarray_set.get(name='ifluor').array))
                mutrans = ifluor/i0
            except Exception as e:
                messages.error(request, 'Could not extract data from fluorescence spectrum: ' + str(e))
        elif mode == XASMode.XMU:
            try:
                energy = np.array(json.loads(file.xasarray_set.get(name='energy').array))
                mutrans = np.array(json.loads(file.xasarray_set.get(name='xmu').array))
                yaxis_title = "Normalized absorption spectrum"
            except Exception as e:
                messages.error(request, 'Could not extract data from normalized absorption spectrum: ' + str(e))
        else:
            messages.error(request, 'Unsupported mode detected!')

        
        if len(list(filter(lambda message: message.level_tag != 'success', messages.get_messages(request)))) == 0:
            murefer = None
            try:
                irefer = np.array(json.loads(file.xasarray_set.get(name='irefer').array))
                murefer = -np.log(irefer/itrans)
            except:
                pass
            plots.append(_file_plot(energy, mutrans, "Energy (eV)", yaxis_title))

    # try getting the doi information
    try:
        # this should probably get cached -> TODO
        cr = Crossref(mailto = "Tom.Schoonjans@diamond.ac.uk") # necessary to end up in the polite pool
        doi = {}
        work = cr.works(ids=file.upload_file_doi)
        doi['title'] = work['message']['title'][0]
        doi['url'] = work['message']['URL']
        doi['year'] = work['message']['published-print']['date-parts'][0][0]
        doi['journal'] = work['message']['short-container-title'][0]
        doi['ncited'] = work['message']['is-referenced-by-count']
        authorlist = ""
        for index, author in enumerate(work['message']['author']):
            givens = author['given'].split()
            for given in givens:
                authorlist += "{}. ".format(given[0])
            family = author['family']
            authorlist += family
            if len(work['message']['author']) > 1:
                    if index == len(work['message']['author']) - 2:
                        authorlist += ' and '
                    elif index != len(work['message']['author']) - 1:
                        authorlist += ', '
                        
        doi['authors'] = authorlist
        doi['citation'] = "{authors}. {title}, <i>{journal}</i> ({year}).".format(authors=doi['authors'], title=doi['title'], journal=doi['journal'], year=doi['year'])
        message = \
                '''By downloading this file, I agree to cite its original authors' manuscript:<br><div style="padding-left: 30px"><a href="{}">{}</a></div><br>as well as the manuscript covering this website:<br>{}'''.format(doi['url'], doi['citation'], OUR_CITATION)
    except Exception as e:
        print(f'file.upload_file_doi: {file.upload_file_doi}')
        traceback.print_exc()
        doi = None
        message = \
'''By downloading this file, I agree to cite the manuscript of this website {}'''.format(doi['citation'], OUR_CITATION)

    form = None
    formset = None
    if request.user.is_staff:
        if request.method == 'POST':
            #for key, values in request.POST.lists():
            #    print(key, values)
            form = XASFileVerificationForm(request.POST, instance=file)
            formset = XASUploadAuxDataVerificationFormSet(request.POST, instance=file)
            if form.is_valid() and formset.is_valid():
                form.save()
                formset.save()
                messages.success(request, 'File information updated')
                formset = XASUploadAuxDataVerificationFormSet(instance=file)
            else:
                messages.error(request, 'Could not update file: check error messages below')
        else:
            form = XASFileVerificationForm(instance=file)
            formset = XASUploadAuxDataVerificationFormSet(instance=file)
    elif request.method == 'POST':
        # naughty
        #for key, values in request.POST.lists():
        #    print(key, values)
        messages.error(request, 'Only staff can make file POST requests!')
        return redirect('xasdb1:index')

    return render(request, 'xasdb1/file.html', {'file' : file, 'plots': plots, 'aux' : file.xasuploadauxdata_set.all(), 'doi' : doi, 'bokeh_version': bokeh_version, 'message': message, 'form': form, 'formset': formset})
    

def _file_plot(xaxis, yaxis, xaxis_name, yaxis_name):
    plot = figure(x_axis_label = xaxis_name, y_axis_label = yaxis_name, plot_width = 500, plot_height = 400, tooltips = [('(x, y)', '($x, $y)')])
    plot.hover.mode = 'vline'
    plot.line(xaxis, yaxis, line_width=2)
    return dict(zip(('script', 'div'), components(plot)))

@login_required(login_url='xasdb1:login')
def download(request, path_id):
    # figure out who this file belongs to
    try:
        # check if path_id corresponds to XDI file
        file = XASFile.objects.get(upload_file=path_id)
        files = (file, file)
    except Exception:
        # check if path_id corresponds to AUX file
        files = None
        for xasfile in XASFile.objects.all():
            for auxfile in xasfile.xasuploadauxdata_set.all():
                if auxfile.aux_file.name == path_id:
                    files = (xasfile, auxfile)
                    break
            else:
                continue
            break

    if files is None:
        messages.error(request, 'The requested file {} does not exist'.format(path_id))
        return redirect('xasdb1:index')

    if not request.user.is_staff and request.user != files[0].uploader and files[0].review_status != XASFile.APPROVED:
        messages.error(request, 'The requested file is not accessible')
        return redirect('xasdb1:index')

    # at this point we are going to serve the file!
    if isinstance(files[1], XASFile):
        # create download entry
        files[1].xasdownloadfile_set.create(downloader=request.user)
    elif isinstance(files[1], XASUploadAuxData):
        files[1].xasdownloadauxdata_set.create(downloader=request.user)


    # inspired by https://stackoverflow.com/q/15246661/1253230
    file_path = settings.MEDIA_ROOT + '/' + path_id
    file_mimetype = mimetypes.guess_type(file_path)
    response = FileResponse(open(file_path, 'rb'), as_attachment=True, content_type=file_mimetype)
    return response
