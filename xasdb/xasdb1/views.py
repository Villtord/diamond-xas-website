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
    return render(request, 'xasdb1/element.html', {'element': element_id})

@login_required
def upload(request):
    if request.method == 'POST':
        form = ModelFormWithFileField(request.POST, request.FILES)
        if form.is_valid():
            # file is saved
            form.save()
            messages.success(request, 'File uploaded')
            return HttpResponseRedirect('/xasdb1/')
    else:
        form = ModelFormWithFileField()
    return render(request, 'xasdb1/upload.html', {'form': form})
