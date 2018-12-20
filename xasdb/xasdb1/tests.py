from django.test import TestCase, Client
from django.test import override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from django.core import mail

from django.conf import settings
from .models import XASFile, XASUploadAuxData
from .views import HOST

from os.path import join, exists, basename, getsize
import tempfile
import os
import unittest
import random
import string
import hashlib
import xraylib as xrl

USERNAME = 'jpwqehfpfewpfhpfweq'
PASSWORD = 'rtkhnwoehfongnrgekrg'
FIRST_NAME = 'John'
LAST_NAME = 'Doe'
EMAIL = 'John.Doe@diamond.ac.uk'
DOI = '10.1016/j.sab.2011.09.011' # xraylib!

SU_USERNAME = 'jhpwejfpfjfpwqjfwq'
SU_PASSWORD = 'jwejfpfjwfepqwjpqfjpfj'
SU_EMAIL = 'admin@xasdb.diamond.ac.uk'

TEMPDIR = tempfile.TemporaryDirectory()

OVERRIDE_SETTINGS = dict(MEDIA_ROOT=TEMPDIR.name, EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend')

UPLOAD_FORMSET_DATA = {
    'form-TOTAL_FORMS': '1',
    'form-INITIAL_FORMS': '0',
    'form-MAX_NUM_FORMS': '10',
    'form-MIN_NUM_FORMS': '0',
}

UPLOAD_FORMSET_DATA_DOUBLE = {
    'form-TOTAL_FORMS': '2',
    'form-INITIAL_FORMS': '0',
    'form-MAX_NUM_FORMS': '10',
    'form-MIN_NUM_FORMS': '0',
}

@override_settings(**OVERRIDE_SETTINGS)
class RegisterTests(TestCase):
    def test_failed_register_from_view1(self):
        c = Client()
        response = c.post(reverse('xasdb1:register'), {'username':'', 'password1':'', 'password2':''})
        self.assertContains(response, 'Your password can&#39;t be too similar to your other personal information.')

    def test_failed_register_from_view2(self):
        c = Client()
        response = c.post(reverse('xasdb1:register'), {'username': USERNAME, 'password1': PASSWORD, 'password2':''})
        self.assertContains(response, 'Your password can&#39;t be too similar to your other personal information.')

    def test_success_register_from_view(self):
        c = Client()
        response = c.post(reverse('xasdb1:register'), {'username': USERNAME, 'password1': PASSWORD, 'password2': PASSWORD, 'first_name': FIRST_NAME, 'last_name': LAST_NAME, 'email': EMAIL}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'Account created successfully: please activate using the email that was sent to you')

@override_settings(**OVERRIDE_SETTINGS)
class LoginTests(TestCase):
    def test_failed_login(self):
        login = self.client.login(username=USERNAME, password=PASSWORD)
        self.assertFalse(login)

    def test_success_login(self):
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD)
        login = self.client.login(username=USERNAME, password=PASSWORD)
        self.assertTrue(login)

    def test_failed_login_from_view(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertContains(response, 'Please enter a correct username and password. Note that both fields may be case-sensitive.')
        # logout
        response = c.get(reverse('xasdb1:logout'), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'Not logged in!')

    def test_success_login_from_view(self):
        c = Client()
        response = c.post(reverse('xasdb1:register'), {'username': USERNAME, 'password1': PASSWORD, 'password2': PASSWORD, 'first_name': FIRST_NAME, 'last_name': LAST_NAME, 'email': EMAIL}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'Account created successfully: please activate using the email that was sent to you')
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        #print(f'response: {response.content}')
        self.assertContains(response, 'This account is inactive.')
        # check mailbox
        self.assertEqual(len(mail.outbox), 2)
        # first email should be sent to user, second to admins
        email_user = mail.outbox[0]
        self.assertEqual(len(email_user.to), 1)
        self.assertEqual(email_user.to[0], EMAIL)
        self.assertEqual(email_user.from_email, settings.SERVER_EMAIL)
        self.assertEqual(email_user.subject, 'Activate your account')
        self.assertTrue('{} {}'.format(FIRST_NAME, LAST_NAME) in email_user.body)

        email_admin = mail.outbox[1]
        self.assertEqual(email_admin.subject, settings.EMAIL_SUBJECT_PREFIX + 'a new user has registered')
        self.assertEqual(email_admin.body, 'Name: {name}\nEmail: {email}\n\nAn activation email has been sent to the new user for confirmation'.format(name=FIRST_NAME + ' ' + LAST_NAME, email=EMAIL))
        self.assertEqual(email_admin.from_email, settings.SERVER_EMAIL)
        self.assertEqual(len(email_admin.to), 1)
        self.assertTrue(email_admin.to[0] in map(lambda x: x[1], settings.ADMINS))
       
        splitted = email_user.body.split('/')
        uid = splitted[-3]
        token = splitted[-2]

        # try activating with bad string
        response = c.get(reverse('xasdb1:activate', args=[uid, "hiwefof-jojofwej"]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'Your activation request has been denied, probably because the link has expired. Please contact the admins to get a new one.')

        # try activate with proper string
        response = c.get(reverse('xasdb1:activate', args=[uid, token]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:login'))
        self.assertContains(response, 'Your account has now been activated. Please login to start uploading and downloading datasets')
       
       # login now
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertContains(response, USERNAME  + ' logged in!')

        # logout
        response = c.get(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

@override_settings(**OVERRIDE_SETTINGS)
class UploadTests(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD, first_name=FIRST_NAME, last_name=LAST_NAME, email=EMAIL)

    def test_without_login(self):
        c = Client()
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp), follow=True)
        self.assertRedirects(response, '/xasdb1/login/?next=/xasdb1/upload/')
        self.assertContains(response, 'Login')
        self.assertEqual(XASFile.objects.count(), 0)
        self.assertFalse(mail.outbox)

    def test_get(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        response = c.get(reverse('xasdb1:upload'))
        #print(f'response: {response.content}')
        self.assertContains(response, '<input type="hidden" name="form-TOTAL_FORMS" value="1" id="id_form-TOTAL_FORMS"><input type="hidden" name="form-INITIAL_FORMS" value="0" id="id_form-INITIAL_FORMS"><input type="hidden" name="form-MIN_NUM_FORMS" value="0" id="id_form-MIN_NUM_FORMS"><input type="hidden" name="form-MAX_NUM_FORMS" value="10" id="id_form-MAX_NUM_FORMS">\n\t\t\n\t\t\t<div class="upload_aux_formset">\n\t\t\t\tDescription\n\t\t\t\t<input type="text" name="form-0-aux_description" maxlength="256" id="id_form-0-aux_description">\n\t\t\t\t\n\n\t\t\t\t<input type="file" name="form-0-aux_file" class="aux_file_class" id="id_form-0-aux_file">\n\t\t\t\t\n\t\t\t</div>\n\t\t\n\t\t\n\t\t<br/>\n\t\t<input type="submit" name="submit" value="Upload!">')

    def test_good_file_bad_doi(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi='rubbish-doi'), follow=True)
        self.assertContains(response, 'Invalid DOI: 404 Client Error: Not Found for url: https://api.crossref.org/works/rubbish-doi')
        self.assertFalse(mail.outbox)

    def test_bad_file_good_doi(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
        self.assertContains(response, 'not an XDI file')
        self.assertFalse(mail.outbox)

    def test_huge_file_good_doi(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(TEMPDIR.name, 'huge.xdi')
        with open(test_file, 'wb') as fp:
            fp.write(os.urandom(20 * 1024 * 1024))
        self.assertTrue(exists(test_file))
        self.assertEqual(getsize(test_file), 20 * 1024 * 1024)
        with open(test_file, 'rb') as fp:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
        self.assertContains(response, 'File size is limited to 10 MB!')
        self.assertFalse(mail.outbox)

    def test_good_file_good_doi(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertEqual(XASFile.objects.count(), 1)
        self.assertEqual(xas_file.upload_file_doi, DOI)
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertTrue(exists(join(TEMPDIR.name, xas_file.upload_file.name)))
        self.assertEqual(xas_file.element, 'Fe')
        self.assertEqual(xas_file.edge, xrl.K_SHELL)
        self.assertEqual(xas_file.uploader.username, USERNAME)
        self.assertEqual(xas_file.review_status, XASFile.PENDING)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, settings.EMAIL_SUBJECT_PREFIX + 'a new dataset has been uploaded')
        self.assertEqual(email.body, 'A new dataset has been uploaded by {} ({}).\nPlease process this submission by visiting {}.'.format(self.user.get_full_name(), self.user.email, HOST + reverse('xasdb1:file', args=[xas_file.id])))
        self.assertEqual(email.from_email, settings.SERVER_EMAIL)
        self.assertEqual(len(email.to), 1)
        self.assertTrue(email.to[0] in map(lambda x: x[1], settings.ADMINS))

    def test_single_aux_single_file_valid(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        self.assertTrue(exists(test_file))
        self.assertTrue(exists(aux_file1))
        aux_desc1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp, open(aux_file1) as aux_fp1:
            # this should work with the defaults in UPLOAD_FORMSET_DATA
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': aux_desc1, 'form-0-aux_file': aux_fp1}), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertEqual(XASFile.objects.count(), 1)
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertTrue(exists(join(TEMPDIR.name, xas_file.upload_file.name)))
        aux_data_set = xas_file.xasuploadauxdata_set.all()
        self.assertTrue(aux_data_set.count() == 1)
        self.assertTrue(exists(join(TEMPDIR.name, aux_data_set[0].aux_file.name)))
        self.assertContains(response, aux_desc1)
        #print(f'response: {response.content}')
        self.assertContains(response, aux_data_set[0].aux_file.name)

    def test_single_aux_single_file_empty(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            # this should work with the defaults in UPLOAD_FORMSET_DATA
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': "", 'form-0-aux_file': None}), follow=True)
        self.assertEqual(XASFile.objects.count(), 1)
        xas_file = XASFile.objects.all()[0]
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertTrue(exists(join(TEMPDIR.name, xas_file.upload_file.name)))
        aux_data_set = xas_file.xasuploadauxdata_set.all()
        self.assertTrue(aux_data_set.count() == 0)
        self.assertNotContains(response, 'Auxiliary data')

    def test_single_aux_single_file_only_description(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        aux_desc1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp:
            # this should work with the defaults in UPLOAD_FORMSET_DATA
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': aux_desc1, 'form-0-aux_file': None}), follow=True)
        self.assertEqual(XASFile.objects.count(), 0)
        self.assertContains(response, 'Unique filename required')

    def test_single_aux_single_file_only_filename(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        self.assertTrue(exists(test_file))
        self.assertTrue(exists(aux_file1))
        with open(test_file) as fp, open(aux_file1) as aux_fp1:
            # this should work with the defaults in UPLOAD_FORMSET_DATA
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': "", 'form-0-aux_file': aux_fp1}), follow=True)
        self.assertEqual(XASFile.objects.count(), 0)
        self.assertContains(response, 'Unique description required')

    def test_single_aux_double_file_valid(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        aux_file2 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_02.xdi')
        self.assertTrue(exists(test_file))
        self.assertTrue(exists(aux_file1))
        self.assertTrue(exists(aux_file2))
        aux_desc1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        aux_desc2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp, open(aux_file1) as aux_fp1, open(aux_file2) as aux_fp2:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA_DOUBLE, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': aux_desc1, 'form-0-aux_file': aux_fp1, 'form-1-aux_description': aux_desc2, 'form-1-aux_file': aux_fp2}), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertEqual(XASFile.objects.count(), 1)
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertTrue(exists(join(TEMPDIR.name, xas_file.upload_file.name)))
        aux_data_set = xas_file.xasuploadauxdata_set.all()
        self.assertTrue(aux_data_set.count() == 2)
        self.assertTrue(exists(join(TEMPDIR.name, aux_data_set[0].aux_file.name)))
        self.assertTrue(exists(join(TEMPDIR.name, aux_data_set[1].aux_file.name)))
        self.assertContains(response, aux_desc1)
        self.assertContains(response, aux_desc2)
        self.assertContains(response, aux_data_set[0].aux_file.name)
        self.assertContains(response, aux_data_set[1].aux_file.name)

    def test_single_aux_double_file_valid_first_empty(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file2 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_02.xdi')
        self.assertTrue(exists(test_file))
        self.assertTrue(exists(aux_file2))
        aux_desc2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp, open(aux_file2) as aux_fp2:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA_DOUBLE, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-1-aux_description': aux_desc2, 'form-1-aux_file': aux_fp2}), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertEqual(XASFile.objects.count(), 1)
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertTrue(exists(join(TEMPDIR.name, xas_file.upload_file.name)))
        aux_data_set = xas_file.xasuploadauxdata_set.all()
        self.assertTrue(aux_data_set.count() == 1)
        self.assertTrue(exists(join(TEMPDIR.name, aux_data_set[0].aux_file.name)))
        self.assertContains(response, aux_desc2)
        self.assertContains(response, aux_data_set[0].aux_file.name)

    def test_single_aux_double_file_valid_second_empty(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        self.assertTrue(exists(test_file))
        self.assertTrue(exists(aux_file1))
        aux_desc1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp, open(aux_file1) as aux_fp1:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA_DOUBLE, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': aux_desc1, 'form-0-aux_file': aux_fp1}), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertEqual(XASFile.objects.count(), 1)
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertTrue(exists(join(TEMPDIR.name, xas_file.upload_file.name)))
        aux_data_set = xas_file.xasuploadauxdata_set.all()
        self.assertTrue(aux_data_set.count() == 1)
        self.assertTrue(exists(join(TEMPDIR.name, aux_data_set[0].aux_file.name)))
        self.assertContains(response, aux_desc1)
        self.assertContains(response, aux_data_set[0].aux_file.name)

    def test_single_aux_double_file_identical_descriptions(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        aux_file2 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_02.xdi')
        self.assertTrue(exists(test_file))
        self.assertTrue(exists(aux_file1))
        self.assertTrue(exists(aux_file2))
        aux_desc = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp, open(aux_file1) as aux_fp1, open(aux_file2) as aux_fp2:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA_DOUBLE, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': aux_desc, 'form-0-aux_file': aux_fp1, 'form-1-aux_description': aux_desc, 'form-1-aux_file': aux_fp2}), follow=True)
        self.assertEqual(XASFile.objects.count(), 0)
        self.assertContains(response, 'Auxiliary data must contain unique descriptions')

    def test_single_aux_double_file_identical_files(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        self.assertTrue(exists(test_file))
        self.assertTrue(exists(aux_file))
        aux_desc1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        aux_desc2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp, open(aux_file) as aux_fp1, open(aux_file) as aux_fp2:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA_DOUBLE, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': aux_desc1, 'form-0-aux_file': aux_fp1, 'form-1-aux_description': aux_desc2, 'form-1-aux_file': aux_fp2}), follow=True)
        self.assertEqual(XASFile.objects.count(), 0)
        self.assertContains(response, 'Auxiliary data must contain unique filenames')

    def test_single_aux_huge_file(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file = join(TEMPDIR.name, 'huge.xdi')
        with open(aux_file, 'wb') as fp:
            fp.write(os.urandom(20 * 1024 * 1024))
        self.assertTrue(exists(aux_file))
        self.assertEqual(getsize(aux_file), 20 * 1024 * 1024)
        self.assertTrue(exists(test_file))
        aux_desc = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp, open(aux_file, 'rb') as aux_fp:
            # this should work with the defaults in UPLOAD_FORMSET_DATA
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': aux_desc, 'form-0-aux_file': aux_fp}), follow=True)
        self.assertContains(response, 'File size is limited to 10 MB!')
        self.assertEqual(XASFile.objects.count(), 0)

@override_settings(**OVERRIDE_SETTINGS)
class ElementTestsCreateAndLoginAsUser(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD)
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_dir = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
            self.assertTrue(exists(test_file))
            with open(test_file) as fp:
                response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
            xas_file_all = XASFile.objects.all()
            xas_file = xas_file_all[xas_file_all.count() - 1]
            self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
            self.assertContains(response, 'File uploaded')
            self.assertContains(response, 'class="bk-root"', count=1)
            self.assertContains(response, 'Submission Status', count=1)
            self.assertContains(response, 'Pending', count=1)
            email = mail.outbox[-1]
            self.assertEqual(email.subject, settings.EMAIL_SUBJECT_PREFIX + 'a new dataset has been uploaded')
            self.assertEqual(email.body, 'A new dataset has been uploaded by {} ({}).\nPlease process this submission by visiting {}.'.format(self.user.get_full_name(), self.user.email, HOST + reverse('xasdb1:file', args=[xas_file.id])))
            self.assertEqual(email.from_email, settings.SERVER_EMAIL)
            self.assertEqual(len(email.to), 1)
            self.assertTrue(email.to[0] in map(lambda x: x[1], settings.ADMINS))

        self.assertEqual(XASFile.objects.count(), len(self.xdi_files))
        self.assertEqual(len(mail.outbox), len(self.xdi_files))

    def test_element_no_files(self):
        # pretty sure there's no uranium data
        response = self.c.get(reverse('xasdb1:element', args=['U']))
        self.assertContains(response, 'No spectra found for U')

    def test_element_Fe_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, '5 spectra found for Fe')

    def test_element_Zn_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Zn']))
        self.assertContains(response, '1 spectrum found for Zn')

@override_settings(**OVERRIDE_SETTINGS)
class ElementTestsCreateAndLoginAsAdmin(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_superuser(username=SU_USERNAME, password=SU_PASSWORD, email=SU_EMAIL)
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': SU_USERNAME, 'password': SU_PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, SU_USERNAME  + ' logged in!')
        test_dir = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
            self.assertTrue(exists(test_file))
            with open(test_file) as fp:
                response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
            xas_file_all = XASFile.objects.all()
            xas_file = xas_file_all[xas_file_all.count() - 1]
            self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
            self.assertContains(response, 'File uploaded')
            self.assertContains(response, 'class="bk-root"', count=1)
            self.assertNotContains(response, 'Submission Status')
            email = mail.outbox[-1]
            self.assertEqual(email.subject, settings.EMAIL_SUBJECT_PREFIX + 'a new dataset has been uploaded')
            self.assertEqual(email.body, 'A new dataset has been uploaded by {} ({}).\nPlease process this submission by visiting {}.'.format(self.user.get_full_name(), self.user.email, HOST + reverse('xasdb1:file', args=[xas_file.id])))
            self.assertEqual(email.from_email, settings.SERVER_EMAIL)
            self.assertEqual(len(email.to), 1)
            self.assertTrue(email.to[0] in map(lambda x: x[1], settings.ADMINS))

        self.assertEqual(XASFile.objects.count(), len(self.xdi_files))

    def test_element_no_files(self):
        # pretty sure there's no uranium data
        response = self.c.get(reverse('xasdb1:element', args=['U']))
        self.assertContains(response, 'No spectra found for U')

    def test_element_Fe_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, '5 spectra found for Fe')

    def test_element_Zn_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Zn']))
        self.assertContains(response, '1 spectrum found for Zn')

@override_settings(**OVERRIDE_SETTINGS)
class ElementTestsCreateAsAdminAndLoginAsUser(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_superuser(username=SU_USERNAME, password=SU_PASSWORD, email=SU_EMAIL)
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': SU_USERNAME, 'password': SU_PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, SU_USERNAME  + ' logged in!')
        test_dir = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
            self.assertTrue(exists(test_file))
            with open(test_file) as fp:
                response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
            xas_file_all = XASFile.objects.all()
            xas_file = xas_file_all[xas_file_all.count() - 1]
            self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
            self.assertContains(response, 'File uploaded')
            self.assertContains(response, 'class="bk-root"', count=1)
            self.assertNotContains(response, 'Submission Status')
            email = mail.outbox[-1]
            self.assertEqual(email.subject, settings.EMAIL_SUBJECT_PREFIX + 'a new dataset has been uploaded')
            self.assertEqual(email.body, 'A new dataset has been uploaded by {} ({}).\nPlease process this submission by visiting {}.'.format(self.user.get_full_name(), self.user.email, HOST + reverse('xasdb1:file', args=[xas_file.id])))
            self.assertEqual(email.from_email, settings.SERVER_EMAIL)
            self.assertEqual(len(email.to), 1)
            self.assertTrue(email.to[0] in map(lambda x: x[1], settings.ADMINS))

        self.assertEqual(XASFile.objects.count(), len(self.xdi_files))
        # logout
        response = self.c.get(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))
        # create and login as regular user
        User.objects.create_user(username=2*USERNAME, password=2*PASSWORD)
        response = self.c.post(reverse('xasdb1:login'), {'username': 2*USERNAME, 'password': 2*PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 2*USERNAME  + ' logged in!')

    def test_element_no_files(self):
        # pretty sure there's no uranium data
        response = self.c.get(reverse('xasdb1:element', args=['U']))
        self.assertContains(response, 'No spectra found for U')

    def test_element_Fe_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, 'No spectra found for Fe')
        # let's approve 3 of them and try again
        for obj in XASFile.objects.filter(element="Fe")[::2]:
            obj.review_status = XASFile.APPROVED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, '3 spectra found for Fe')
        # now lets reject them
        for obj in XASFile.objects.filter(element="Fe")[::2]:
            obj.review_status = XASFile.REJECTED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, 'No spectra found for Fe')

    def test_element_Zn_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Zn']))
        self.assertContains(response, 'No spectra found for Zn')

@override_settings(**OVERRIDE_SETTINGS)
class ElementTestsCreateAsAdminAndLogout(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_superuser(username=SU_USERNAME, password=SU_PASSWORD, email=SU_EMAIL)
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': SU_USERNAME, 'password': SU_PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, SU_USERNAME  + ' logged in!')
        test_dir = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
            self.assertTrue(exists(test_file))
            with open(test_file) as fp:
                response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
            xas_file_all = XASFile.objects.all()
            xas_file = xas_file_all[xas_file_all.count() - 1]
            self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
            self.assertContains(response, 'File uploaded')
            self.assertContains(response, 'class="bk-root"', count=1)
            self.assertNotContains(response, 'Submission Status')
            email = mail.outbox[-1]
            self.assertEqual(email.subject, settings.EMAIL_SUBJECT_PREFIX + 'a new dataset has been uploaded')
            self.assertEqual(email.body, 'A new dataset has been uploaded by {} ({}).\nPlease process this submission by visiting {}.'.format(self.user.get_full_name(), self.user.email, HOST + reverse('xasdb1:file', args=[xas_file.id])))
            self.assertEqual(email.from_email, settings.SERVER_EMAIL)
            self.assertEqual(len(email.to), 1)
            self.assertTrue(email.to[0] in map(lambda x: x[1], settings.ADMINS))

        self.assertEqual(XASFile.objects.count(), len(self.xdi_files))
        # logout
        response = self.c.get(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

    def test_element_no_files(self):
        # pretty sure there's no uranium data
        response = self.c.get(reverse('xasdb1:element', args=['U']))
        self.assertContains(response, 'No spectra found for U')

    def test_element_Fe_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, 'No spectra found for Fe')
        # let's approve 3 of them and try again
        for obj in XASFile.objects.filter(element="Fe")[::2]:
            obj.review_status = XASFile.APPROVED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, '3 spectra found for Fe')
        # now lets reject them
        for obj in XASFile.objects.filter(element="Fe")[::2]:
            obj.review_status = XASFile.REJECTED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, 'No spectra found for Fe')

    def test_element_Zn_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Zn']))
        self.assertContains(response, 'No spectra found for Zn')

@override_settings(**OVERRIDE_SETTINGS)
class FileTestsCreateAsAdmin(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_superuser(username=SU_USERNAME, password=SU_PASSWORD, email=SU_EMAIL)
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': SU_USERNAME, 'password': SU_PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, SU_USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertEqual(XASFile.objects.count(), 1)
        # logout
        response = self.c.get(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

    def test_file_no_login(self):
        file = XASFile.objects.all()[0]
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        file.review_status = XASFile.REJECTED
        file.save()
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')

    def test_file_login_as_user(self):
        User.objects.create_user(username=USERNAME, password=PASSWORD)
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        file = XASFile.objects.all()[0]
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')

    def test_file_login_as_admin(self):
        response = self.c.post(reverse('xasdb1:login'), {'username': SU_USERNAME, 'password': SU_PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, SU_USERNAME  + ' logged in!')
        file = XASFile.objects.all()[0]
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')
        self.assertContains(response, 'Review status')
        self.assertContains(response, 'selected>Pending')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')
        self.assertContains(response, 'Review status')
        self.assertContains(response, 'selected>Approved')

@override_settings(**OVERRIDE_SETTINGS)
class FileTestsCreateAsUser(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        User.objects.create_user(username=USERNAME, password=PASSWORD)
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertEqual(XASFile.objects.count(), 1)
        # logout
        response = self.c.get(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

    def test_file_no_login(self):
        file = XASFile.objects.all()[0]
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')

    def test_file_login_as_user(self):
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        file = XASFile.objects.all()[0]
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertContains(response, 'Submission Status')
        self.assertContains(response, 'Pending')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertContains(response, 'Submission Status')
        self.assertContains(response, 'Approved')
        file.review_status = XASFile.REJECTED
        file.save()
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertContains(response, 'Submission Status')
        self.assertContains(response, 'Rejected')

    def test_file_login_as_admin(self):
        User.objects.create_superuser(username=SU_USERNAME, password=SU_PASSWORD, email=SU_EMAIL)
        response = self.c.post(reverse('xasdb1:login'), {'username': SU_USERNAME, 'password': SU_PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, SU_USERNAME  + ' logged in!')
        file = XASFile.objects.all()[0]
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')
        self.assertContains(response, 'Review status')
        self.assertContains(response, 'selected>Pending')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')
        self.assertContains(response, 'Review status')
        self.assertContains(response, 'selected>Approved')

@override_settings(**OVERRIDE_SETTINGS)
class FileTestsCheckContents(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD, first_name=FIRST_NAME, last_name=LAST_NAME, email=EMAIL)
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_dir = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
            self.assertTrue(exists(test_file))
            with open(test_file) as fp:
                response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
            xas_file_all = XASFile.objects.all()
            xas_file = xas_file_all[xas_file_all.count() - 1]
            self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
            self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertEqual(XASFile.objects.count(), len(self.xdi_files))

    def test_contents_presence(self):
        files = XASFile.objects.all()
        for file in files:
            #print(f"{file.upload_file.name}")
            response = self.c.get(reverse('xasdb1:file', args=[file.id]), follow=True)
            self.assertContains(response, 'class="bk-root"', count=1)
            self.assertContains(response, f'{FIRST_NAME} {LAST_NAME}')
            # self.assertNotContains(response, 'unknown')

@override_settings(**OVERRIDE_SETTINGS)
class FileTestsDownload(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD)
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        self.assertTrue(exists(test_file))
        self.assertTrue(exists(aux_file1))
        aux_desc1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp, open(aux_file1) as aux_fp1:
            # this should work with the defaults in UPLOAD_FORMSET_DATA
            response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, **{'upload_file':fp, 'upload_file_doi':DOI, 'form-0-aux_description': aux_desc1, 'form-0-aux_file': aux_fp1}), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertEqual(XASFile.objects.count(), 1)
        xas_file = XASFile.objects.all()[0]
        self.upload_file_name = xas_file.upload_file.name
        self.aux_file_name = xas_file.xasuploadauxdata_set.get(pk=1).aux_file.name
        # logout
        response = self.c.get(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))
        # calculate file checksums
        hash_md5 = hashlib.md5()
        with (open(test_file, 'rb')) as f:
            for chunk in f:
                hash_md5.update(chunk)
        self.xdi_checksum = hash_md5.hexdigest()
        hash_md5 = hashlib.md5()
        with (open(aux_file1, 'rb')) as f:
            for chunk in f:
                hash_md5.update(chunk)
        self.aux_checksum = hash_md5.hexdigest()

    def test_download_no_login(self):
        response = self.c.post(reverse('xasdb1:download', args=[self.upload_file_name]), follow=True)
        self.assertRedirects(response, '/xasdb1/login/?next=/xasdb1/download/' + self.upload_file_name + '/')
        self.assertContains(response, 'Login')
        response = self.c.post(reverse('xasdb1:download', args=[self.aux_file_name]), follow=True)
        self.assertRedirects(response, '/xasdb1/login/?next=/xasdb1/download/' + self.aux_file_name + '/')
        self.assertContains(response, 'Login')
        obj = XASFile.objects.get(pk=1)
        obj.review_status = XASFile.APPROVED
        obj.save()
        response = self.c.post(reverse('xasdb1:download', args=[self.upload_file_name]), follow=True)
        self.assertRedirects(response, '/xasdb1/login/?next=/xasdb1/download/' + self.upload_file_name + '/')
        self.assertContains(response, 'Login')
        response = self.c.post(reverse('xasdb1:download', args=[self.aux_file_name]), follow=True)
        self.assertRedirects(response, '/xasdb1/login/?next=/xasdb1/download/' + self.aux_file_name + '/')
        self.assertContains(response, 'Login')

    def test_download_login_as_uploader(self):
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        response = self.c.post(reverse('xasdb1:download', args=[self.upload_file_name]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="{}"'.format(basename(self.upload_file_name)))
        hash_md5 = hashlib.md5()
        for chunk in response.streaming_content:
            hash_md5.update(chunk)
        self.assertEqual(hash_md5.hexdigest(), self.xdi_checksum)

        # test download counter
        file = XASFile.objects.get(pk=1)
        self.assertEqual(file.xasdownloadfile_set.count(), 1)
        downloadfile = file.xasdownloadfile_set.get(pk=1)
        self.assertEqual(downloadfile.downloader, self.user)
        ndownloads = random.randint(1, 10)
        for i in range(ndownloads):
            response = self.c.post(reverse('xasdb1:download', args=[self.upload_file_name]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="{}"'.format(basename(self.upload_file_name)))
            hash_md5 = hashlib.md5()
            for chunk in response.streaming_content:
                hash_md5.update(chunk)
            self.assertEqual(hash_md5.hexdigest(), self.xdi_checksum)
        self.assertEqual(file.xasdownloadfile_set.count(), ndownloads + 1)

        response = self.c.post(reverse('xasdb1:download', args=[self.aux_file_name]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="{}"'.format(basename(self.aux_file_name)))
        hash_md5 = hashlib.md5()
        for chunk in response.streaming_content:
            hash_md5.update(chunk)
        self.assertEqual(hash_md5.hexdigest(), self.aux_checksum)

        # test download counter
        file = XASFile.objects.get(pk=1)
        self.assertEqual(file.xasuploadauxdata_set.count(), 1)
        aux_file = file.xasuploadauxdata_set.get(pk=1)
        self.assertEqual(aux_file.xasdownloadauxdata_set.count(), 1)
        aux_download_data = aux_file.xasdownloadauxdata_set.get(pk=1)
        self.assertEqual(aux_download_data.downloader, self.user)
        ndownloads = random.randint(1, 10)
        for i in range(ndownloads):
            response = self.c.post(reverse('xasdb1:download', args=[self.aux_file_name]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="{}"'.format(basename(self.aux_file_name)))
            hash_md5 = hashlib.md5()
            for chunk in response.streaming_content:
                hash_md5.update(chunk)
            self.assertEqual(hash_md5.hexdigest(), self.aux_checksum)
        self.assertEqual(aux_file.xasdownloadauxdata_set.count(), ndownloads + 1)

        # test downloading non-existent file
        response = self.c.post(reverse('xasdb1:download', args=["non-existent-file.xdi"]), follow=True)
        self.assertRedirects(response, '/xasdb1/')
        self.assertContains(response, 'The requested file non-existent-file.xdi does not exist')

    def test_download_login_as_other_user(self):
        new_user = User.objects.create_user(username=2*USERNAME, password=2*PASSWORD)
        response = self.c.post(reverse('xasdb1:login'), {'username': 2*USERNAME, 'password': 2*PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 2*USERNAME  + ' logged in!')
        response = self.c.post(reverse('xasdb1:download', args=[self.upload_file_name]), follow=True)
        self.assertRedirects(response, '/xasdb1/')
        self.assertContains(response, 'The requested file is not accessible')
        response = self.c.post(reverse('xasdb1:download', args=[self.aux_file_name]), follow=True)
        self.assertRedirects(response, '/xasdb1/')
        self.assertContains(response, 'The requested file is not accessible')

        # now approve the file to make it accessible for this user
        obj = XASFile.objects.get(pk=1)
        obj.review_status = XASFile.APPROVED
        obj.save()
        response = self.c.post(reverse('xasdb1:download', args=[self.upload_file_name]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="{}"'.format(basename(self.upload_file_name)))
        hash_md5 = hashlib.md5()
        for chunk in response.streaming_content:
            hash_md5.update(chunk)
        self.assertEqual(hash_md5.hexdigest(), self.xdi_checksum)

        # test download counter
        file = XASFile.objects.get(pk=1)
        self.assertEqual(file.xasdownloadfile_set.count(), 1)
        downloadfile = file.xasdownloadfile_set.get(pk=1)
        self.assertEqual(downloadfile.downloader, new_user)
        ndownloads = random.randint(1, 10)
        for i in range(ndownloads):
            response = self.c.post(reverse('xasdb1:download', args=[self.upload_file_name]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="{}"'.format(basename(self.upload_file_name)))
            hash_md5 = hashlib.md5()
            for chunk in response.streaming_content:
                hash_md5.update(chunk)
            self.assertEqual(hash_md5.hexdigest(), self.xdi_checksum)
        self.assertEqual(file.xasdownloadfile_set.count(), ndownloads + 1)

        response = self.c.post(reverse('xasdb1:download', args=[self.aux_file_name]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="{}"'.format(basename(self.aux_file_name)))
        hash_md5 = hashlib.md5()
        for chunk in response.streaming_content:
            hash_md5.update(chunk)
        self.assertEqual(hash_md5.hexdigest(), self.aux_checksum)

        # test download counter
        file = XASFile.objects.get(pk=1)
        self.assertEqual(file.xasuploadauxdata_set.count(), 1)
        aux_file = file.xasuploadauxdata_set.get(pk=1)
        self.assertEqual(aux_file.xasdownloadauxdata_set.count(), 1)
        aux_download_data = aux_file.xasdownloadauxdata_set.get(pk=1)
        self.assertEqual(aux_download_data.downloader, new_user)
        ndownloads = random.randint(1, 10)
        for i in range(ndownloads):
            response = self.c.post(reverse('xasdb1:download', args=[self.aux_file_name]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="{}"'.format(basename(self.aux_file_name)))
            hash_md5 = hashlib.md5()
            for chunk in response.streaming_content:
                hash_md5.update(chunk)
            self.assertEqual(hash_md5.hexdigest(), self.aux_checksum)
        self.assertEqual(aux_file.xasdownloadauxdata_set.count(), ndownloads + 1)

        # test downloading non-existent file
        response = self.c.post(reverse('xasdb1:download', args=["non-existent-file.xdi"]), follow=True)
        self.assertRedirects(response, '/xasdb1/')
        self.assertContains(response, 'The requested file non-existent-file.xdi does not exist')

@override_settings(**OVERRIDE_SETTINGS)
class FileTestsVerify(TestCase):
    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD)
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        aux_file2 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_02.xdi')
        aux_file3 = join(settings.BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_03.xdi')
        self.assertTrue(exists(test_file))
        self.assertTrue(exists(aux_file1))
        self.assertTrue(exists(aux_file2))
        self.assertTrue(exists(aux_file3))
        aux_desc1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        aux_desc2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        aux_desc3 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with open(test_file) as fp, open(aux_file1) as aux_fp1, open(aux_file2) as aux_fp2, open(aux_file3) as aux_fp3:
            # this should work with the defaults in UPLOAD_FORMSET_DATA
            response = self.c.post( \
                    reverse('xasdb1:upload'), \
                    dict(UPLOAD_FORMSET_DATA, **{ \
                        'upload_file':fp, \
                        'upload_file_doi':DOI, \
                        'form-TOTAL_FORMS': '3', \
                        'form-0-aux_description': aux_desc1, \
                        'form-0-aux_file': aux_fp1, \
                        'form-1-aux_description': aux_desc2, \
                        'form-1-aux_file': aux_fp2, \
                        'form-2-aux_description': aux_desc3, \
                        'form-2-aux_file': aux_fp3, \
                        } 
                    ), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertEqual(XASFile.objects.count(), 1)
        self.xas_file = xas_file
        self.aux_file_description1 = xas_file.xasuploadauxdata_set.get(pk=1).aux_description
        self.aux_file_description2 = xas_file.xasuploadauxdata_set.get(pk=2).aux_description
        self.aux_file_description3 = xas_file.xasuploadauxdata_set.get(pk=3).aux_description
        # logout
        response = self.c.get(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

    def test_login_as_same_user(self):
        # users should never be able to access forms or do POST requests
        login = self.c.login(username=USERNAME, password=PASSWORD)
        self.assertTrue(login)
        response = self.c.get(reverse('xasdb1:file', args=[self.xas_file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {self.xas_file.sample_name}')
        self.assertContains(response, 'Submission Status')
        self.assertContains(response, 'Pending')
        response = self.c.post(reverse('xasdb1:file', args=[self.xas_file.id]), {'review_status': XASFile.APPROVED}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'Only staff can make file POST requests!')

    def test_login_as_different_user(self):
        # users should never be able to access forms or do POST requests
        new_user = User.objects.create_user(username=2*USERNAME, password=2*PASSWORD)
        login = self.c.login(username=2*USERNAME, password=2*PASSWORD)
        self.assertTrue(login)
        response = self.c.get(reverse('xasdb1:file', args=[self.xas_file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')
        response = self.c.post(reverse('xasdb1:file', args=[self.xas_file.id]), {'review_status': XASFile.APPROVED}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')

    def test_without_login(self):
        # users should never be able to access forms or do POST requests
        response = self.c.get(reverse('xasdb1:file', args=[self.xas_file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')
        response = self.c.post(reverse('xasdb1:file', args=[self.xas_file.id]), {'review_status': XASFile.APPROVED}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')

    def test_as_admin(self):
        User.objects.create_superuser(username=SU_USERNAME, password=SU_PASSWORD, email=SU_EMAIL)
        login = self.c.login(username=SU_USERNAME, password=SU_PASSWORD)
        self.assertTrue(login)

        BASE_DICT = model_to_dict(self.xas_file) # convert instance do POST style dict
        BASE_DICT.update(**{\
            'xasuploadauxdata_set-TOTAL_FORMS': '3', \
            'xasuploadauxdata_set-INITIAL_FORMS': '3', \
            'xasuploadauxdata_set-MIN_NUM_FORMS': '0', \
            'xasuploadauxdata_set-MAX_NUM_FORMS': '10', \
            'xasuploadauxdata_set-0-id' : self.xas_file.xasuploadauxdata_set.get(pk=1).id, \
            'xasuploadauxdata_set-0-aux_description' : self.xas_file.xasuploadauxdata_set.get(pk=1).aux_description, \
            'xasuploadauxdata_set-1-id' : self.xas_file.xasuploadauxdata_set.get(pk=2).id, \
            'xasuploadauxdata_set-1-aux_description' : self.xas_file.xasuploadauxdata_set.get(pk=2).aux_description, \
            'xasuploadauxdata_set-2-id' : self.xas_file.xasuploadauxdata_set.get(pk=3).id, \
            'xasuploadauxdata_set-2-aux_description' : self.xas_file.xasuploadauxdata_set.get(pk=3).aux_description \
        })
        
        response = self.c.get(reverse('xasdb1:file', args=[self.xas_file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {self.xas_file.sample_name}')
        self.assertNotContains(response, 'Submission Status')
        self.assertContains(response, 'Review status')
        self.assertContains(response, 'selected>Pending')
        self.assertEqual(self.xas_file.review_status, XASFile.PENDING)
        response = self.c.post( \
            reverse('xasdb1:file', args=[self.xas_file.id]),\
            dict(BASE_DICT,
                **{\
                    'review_status': XASFile.APPROVED, \
                    'xasuploadauxdata_set-1-aux_description' : 'new-description', \
                }\
            ),\
            follow=True)
        self.assertContains(response, 'Review status')
        self.assertContains(response, 'selected>Approved')
        #print(f'response: {response.content}')
        self.xas_file = XASFile.objects.all()[0]
        self.aux_file_description2 = 'new-description'
        self.assertEqual(self.xas_file.review_status, XASFile.APPROVED)
        self.assertEqual(self.aux_file_description1, self.xas_file.xasuploadauxdata_set.get(pk=1).aux_description)
        self.assertEqual(self.aux_file_description2, self.xas_file.xasuploadauxdata_set.get(pk=2).aux_description)
        self.assertEqual(self.aux_file_description3, self.xas_file.xasuploadauxdata_set.get(pk=3).aux_description)
        self.assertContains(response, 'File information updated')
        self.assertNotContains(response, 'Could not update file: check error messages below')

        # try setting descriptions to identical strings
        response = self.c.post( \
            reverse('xasdb1:file', args=[self.xas_file.id]),\
            dict(BASE_DICT,
                **{\
                'review_status': XASFile.REJECTED, \
                    'xasuploadauxdata_set-0-aux_description' : 'some-string', \
                    'xasuploadauxdata_set-1-aux_description' : 'some-string', \
                    'xasuploadauxdata_set-2-aux_description' : self.xas_file.xasuploadauxdata_set.get(pk=3).aux_description
                }\
            ),\
            follow=True)
        self.assertContains(response, 'Review status')
        self.assertContains(response, 'selected>Rejected')
        self.assertContains(response, 'Could not update file: check error messages below')
        self.assertContains(response, 'Auxiliary data must contain unique descriptions')
        self.xas_file = XASFile.objects.all()[0]
        self.assertEqual(self.xas_file.review_status, XASFile.APPROVED)
        self.assertEqual(self.aux_file_description1, self.xas_file.xasuploadauxdata_set.get(pk=1).aux_description)
        self.assertEqual(self.aux_file_description2, self.xas_file.xasuploadauxdata_set.get(pk=2).aux_description)
        self.assertEqual(self.aux_file_description3, self.xas_file.xasuploadauxdata_set.get(pk=3).aux_description)
        
        # try setting an empty description
        response = self.c.post( \
            reverse('xasdb1:file', args=[self.xas_file.id]),\
            dict(BASE_DICT,
                **{\
                    'review_status': XASFile.PENDING, \
                    'xasuploadauxdata_set-0-aux_description' : 'some-string', \
                    'xasuploadauxdata_set-1-aux_description' : '', \
                    'xasuploadauxdata_set-2-aux_description' : self.xas_file.xasuploadauxdata_set.get(pk=3).aux_description
                }\
            ),\
            follow=True)
        self.xas_file = XASFile.objects.all()[0]
        self.assertEqual(self.xas_file.review_status, XASFile.APPROVED)
        self.assertContains(response, 'Review status')
        self.assertContains(response, 'selected>Pending')
        self.assertContains(response, 'Could not update file: check error messages below')
        self.assertContains(response, 'Unique description required')
        self.assertContains(response, 'Valid auxiliary data consists of a unique description and a unique filename')
        self.assertEqual(self.aux_file_description1, self.xas_file.xasuploadauxdata_set.get(pk=1).aux_description)
        self.assertEqual(self.aux_file_description2, self.xas_file.xasuploadauxdata_set.get(pk=2).aux_description)
        self.assertEqual(self.aux_file_description3, self.xas_file.xasuploadauxdata_set.get(pk=3).aux_description)
    
        # delete second file
        response = self.c.post( \
            reverse('xasdb1:file', args=[self.xas_file.id]),\
            dict(BASE_DICT,
                **{\
                    'review_status': XASFile.PENDING, \
                    'xasuploadauxdata_set-1-DELETE' : 'on'
                }\
            ),\
            follow=True)
        self.xas_file = XASFile.objects.all()[0]
        self.assertEqual(self.xas_file.review_status, XASFile.PENDING)
        self.assertContains(response, 'File information updated')
        self.assertContains(response, 'Review status')
        self.assertContains(response, 'selected>Pending')
        self.assertNotContains(response, 'Could not update file: check error messages below')
        self.assertEqual(self.xas_file.xasuploadauxdata_set.count(), 2)
        self.assertEqual(self.aux_file_description1, self.xas_file.xasuploadauxdata_set.get(pk=1).aux_description)
        self.assertEqual(self.aux_file_description3, self.xas_file.xasuploadauxdata_set.get(pk=3).aux_description)

