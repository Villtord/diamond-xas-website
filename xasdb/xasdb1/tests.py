from django.test import TestCase, Client
from django.test import override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from xasdb.settings import BASE_DIR
from .models import XASFile, XASUploadAuxData

from os.path import join, exists, basename, getsize
import tempfile
import os
import unittest
import random
import string
import hashlib

USERNAME = 'jpwqehfpfewpfhpfweq'
PASSWORD = 'rtkhnwoehfongnrgekrg'
FIRST_NAME = 'John'
LAST_NAME = 'Doe'
EMAIL = 'John.Doe@diamond.ac.uk'
DOI = '10.1016/j.sab.2011.09.011' # xraylib!

TEMPDIR = tempfile.TemporaryDirectory()

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
        self.assertContains(response, 'Account created successfully')

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
        response = c.post(reverse('xasdb1:logout'), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'Not logged in!')

    def test_success_login_from_view(self):
        c = Client()
        response = c.post(reverse('xasdb1:register'), {'username': USERNAME, 'password1': PASSWORD, 'password2': PASSWORD, 'first_name': FIRST_NAME, 'last_name': LAST_NAME, 'email': EMAIL}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'Account created successfully')
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        # logout
        response = c.post(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

@override_settings(MEDIA_ROOT=TEMPDIR.name)
class UploadTests(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD)

    def test_without_login(self):
        c = Client()
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp), follow=True)
        self.assertRedirects(response, '/xasdb1/login/?next=/xasdb1/upload/')
        self.assertContains(response, 'Login')
        self.assertEqual(XASFile.objects.count(), 0)

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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi='rubbish-doi'), follow=True)
        self.assertContains(response, 'Invalid DOI: 404 Client Error: Not Found for url: https://api.crossref.org/works/rubbish-doi')

    def test_bad_file_good_doi(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
        self.assertContains(response, 'not an XDI file')

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

    def test_good_file_good_doi(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
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
        self.assertEqual(xas_file.atomic_number, 26)
        self.assertEqual(xas_file.element, 'Fe')
        self.assertEqual(xas_file.edge, 'K')
        self.assertEqual(xas_file.uploader.username, USERNAME)
        self.assertEqual(xas_file.review_status, XASFile.PENDING)

    def test_single_aux_single_file_valid(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        aux_file2 = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_02.xdi')
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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file2 = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_02.xdi')
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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        aux_file2 = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_02.xdi')
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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
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
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
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

@override_settings(MEDIA_ROOT=TEMPDIR.name)
class ElementTestsCreateAndLoginAsUser(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD)
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_dir = join(BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
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

@override_settings(MEDIA_ROOT=TEMPDIR.name)
class ElementTestsCreateAndLoginAsAdmin(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_superuser(username=USERNAME, password=PASSWORD, email='test@example.com')
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_dir = join(BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
            self.assertTrue(exists(test_file))
            with open(test_file) as fp:
                response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
            xas_file_all = XASFile.objects.all()
            xas_file = xas_file_all[xas_file_all.count() - 1]
            self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
            self.assertContains(response, 'File uploaded')
            self.assertContains(response, 'class="bk-root"', count=1)
            self.assertNotContains(response, 'Submission Status')
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

@override_settings(MEDIA_ROOT=TEMPDIR.name)
class ElementTestsCreateAsAdminAndLoginAsUser(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        User.objects.create_superuser(username=USERNAME, password=PASSWORD, email='test@example.com')
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_dir = join(BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
            self.assertTrue(exists(test_file))
            with open(test_file) as fp:
                response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
            xas_file_all = XASFile.objects.all()
            xas_file = xas_file_all[xas_file_all.count() - 1]
            self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
            self.assertContains(response, 'File uploaded')
            self.assertContains(response, 'class="bk-root"', count=1)
            self.assertNotContains(response, 'Submission Status')
        self.assertEqual(XASFile.objects.count(), len(self.xdi_files))
        # logout
        response = self.c.post(reverse('xasdb1:logout'))
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
        for obj in XASFile.objects.filter(atomic_number=26)[::2]:
            obj.review_status = XASFile.APPROVED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, '3 spectra found for Fe')
        # now lets reject them
        for obj in XASFile.objects.filter(atomic_number=26)[::2]:
            obj.review_status = XASFile.REJECTED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, 'No spectra found for Fe')

    def test_element_Zn_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Zn']))
        self.assertContains(response, 'No spectra found for Zn')

@override_settings(MEDIA_ROOT=TEMPDIR.name)
class ElementTestsCreateAsAdminAndLogout(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        User.objects.create_superuser(username=USERNAME, password=PASSWORD, email='test@example.com')
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_dir = join(BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
            self.assertTrue(exists(test_file))
            with open(test_file) as fp:
                response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
            xas_file_all = XASFile.objects.all()
            xas_file = xas_file_all[xas_file_all.count() - 1]
            self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
            self.assertContains(response, 'File uploaded')
            self.assertContains(response, 'class="bk-root"', count=1)
            self.assertNotContains(response, 'Submission Status')
        self.assertEqual(XASFile.objects.count(), len(self.xdi_files))
        # logout
        response = self.c.post(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

    def test_element_no_files(self):
        # pretty sure there's no uranium data
        response = self.c.get(reverse('xasdb1:element', args=['U']))
        self.assertContains(response, 'No spectra found for U')

    def test_element_Fe_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, 'No spectra found for Fe')
        # let's approve 3 of them and try again
        for obj in XASFile.objects.filter(atomic_number=26)[::2]:
            obj.review_status = XASFile.APPROVED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, '3 spectra found for Fe')
        # now lets reject them
        for obj in XASFile.objects.filter(atomic_number=26)[::2]:
            obj.review_status = XASFile.REJECTED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, 'No spectra found for Fe')

    def test_element_Zn_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Zn']))
        self.assertContains(response, 'No spectra found for Zn')

@override_settings(MEDIA_ROOT=TEMPDIR.name)
class FileTestsCreateAsAdmin(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        User.objects.create_superuser(username=2*USERNAME, password=2*PASSWORD, email='test@example.com')
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': 2*USERNAME, 'password': 2*PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 2*USERNAME  + ' logged in!')
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertEqual(XASFile.objects.count(), 1)
        # logout
        response = self.c.post(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

    def test_file_no_login(self):
        file = XASFile.objects.all()[0]
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        file.review_status = XASFile.REJECTED
        file.save()
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')

    def test_file_login_as_user(self):
        User.objects.create_user(username=USERNAME, password=PASSWORD)
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        file = XASFile.objects.all()[0]
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')

    def test_file_login_as_admin(self):
        response = self.c.post(reverse('xasdb1:login'), {'username': 2*USERNAME, 'password': 2*PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 2*USERNAME  + ' logged in!')
        file = XASFile.objects.all()[0]
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')

@override_settings(MEDIA_ROOT=TEMPDIR.name)
class FileTestsCreateAsUser(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        User.objects.create_user(username=USERNAME, password=PASSWORD)
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = self.c.post(reverse('xasdb1:upload'), dict(UPLOAD_FORMSET_DATA, upload_file=fp, upload_file_doi=DOI), follow=True)
        xas_file = XASFile.objects.all()[0]
        self.assertRedirects(response, reverse('xasdb1:file', args=[xas_file.id]))
        self.assertContains(response, 'File uploaded')
        self.assertContains(response, 'class="bk-root"', count=1)
        self.assertEqual(XASFile.objects.count(), 1)
        # logout
        response = self.c.post(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

    def test_file_no_login(self):
        file = XASFile.objects.all()[0]
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'The requested file is not accessible')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')

    def test_file_login_as_user(self):
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        file = XASFile.objects.all()[0]
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertContains(response, 'Submission Status')
        self.assertContains(response, 'Pending')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertContains(response, 'Submission Status')
        self.assertContains(response, 'Approved')
        file.review_status = XASFile.REJECTED
        file.save()
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertContains(response, 'Submission Status')
        self.assertContains(response, 'Rejected')

    def test_file_login_as_admin(self):
        User.objects.create_superuser(username=2*USERNAME, password=2*PASSWORD, email='test@example.com')
        response = self.c.post(reverse('xasdb1:login'), {'username': 2*USERNAME, 'password': 2*PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 2*USERNAME  + ' logged in!')
        file = XASFile.objects.all()[0]
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        self.assertNotContains(response, 'Submission Status')

@override_settings(MEDIA_ROOT=TEMPDIR.name)
class FileTestsCheckContents(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD, first_name=FIRST_NAME, last_name=LAST_NAME, email=EMAIL)
        # populate database with all good xdi files
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_dir = join(BASE_DIR, 'xasdb1', 'testdata', 'good')
        self.xdi_files = os.listdir(test_dir)
        self.assertTrue(len(self.xdi_files) > 0)
        
        for xdi_file in self.xdi_files:
            test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', xdi_file)
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
            response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
            self.assertContains(response, 'class="bk-root"', count=1)
            self.assertContains(response, f'{FIRST_NAME} {LAST_NAME} ({EMAIL})')
            # self.assertNotContains(response, 'unknown')

@override_settings(MEDIA_ROOT=TEMPDIR.name)
class FileTestsDownload(TestCase):

    def setUp(self):
        # let's assume that registering works fine via the view..
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD)
        self.c = Client()
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        aux_file1 = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
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
        response = self.c.post(reverse('xasdb1:logout'))
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
