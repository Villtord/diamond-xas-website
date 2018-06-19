from django.test import TestCase, Client
from django.test import override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from xasdb.settings import BASE_DIR
from .models import XASFile

from os.path import join, exists
import tempfile
import os

USERNAME = 'jpwqehfpfewpfhpfweq'
PASSWORD = 'rtkhnwoehfongnrgekrg'

TEMPDIR = tempfile.TemporaryDirectory()

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
        response = c.post(reverse('xasdb1:register'), {'username': USERNAME, 'password1': PASSWORD, 'password2': PASSWORD}, follow=True)
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
        response = c.post(reverse('xasdb1:register'), {'username': USERNAME, 'password1': PASSWORD, 'password2': PASSWORD}, follow=True)
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
        return
        c = Client()
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), {'name': 'upload_file', 'upload_file': fp}, follow=True)
        self.assertRedirects(response, '/xasdb1/login/?next=/xasdb1/upload/')
        self.assertContains(response, 'Login')
        self.assertEqual(len(XASFile.objects.all()), 0)

    def test_good_file(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'good', 'fe3c_rt.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), {'name': 'upload_file', 'upload_file': fp}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'File uploaded')
        self.assertEqual(len(XASFile.objects.all()), 1)
        xas_file = XASFile.objects.get(id = 1)
        self.assertTrue(exists(join(TEMPDIR.name, xas_file.upload_file.name)))
        self.assertEqual(xas_file.atomic_number, 26)
        self.assertEqual(xas_file.element, 'Fe')
        self.assertEqual(xas_file.edge, 'K')
        self.assertEqual(xas_file.uploader.username, USERNAME)
        self.assertEqual(xas_file.review_status, XASFile.PENDING)

    def test_bad_file(self):
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        test_file = join(BASE_DIR, 'xasdb1', 'testdata', 'bad', 'bad_01.xdi')
        self.assertTrue(exists(test_file))
        with open(test_file) as fp:
            response = c.post(reverse('xasdb1:upload'), {'name': 'upload_file', 'upload_file': fp}, follow=True)
        self.assertContains(response, 'not an XDI file')

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
                response = self.c.post(reverse('xasdb1:upload'), {'name': 'upload_file', 'upload_file': fp}, follow=True)
            self.assertRedirects(response, reverse('xasdb1:index'))
            self.assertContains(response, 'File uploaded')
        self.assertEqual(len(XASFile.objects.all()), len(self.xdi_files))

    def test_element_no_files(self):
        # pretty sure there's no uranium data
        response = self.c.get(reverse('xasdb1:element', args=['U']))
        self.assertContains(response, 'No spectra found for U')

    def test_element_Fe_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, '5 spectra found for Fe')

    def test_element_Zn_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Zn']))

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
                response = self.c.post(reverse('xasdb1:upload'), {'name': 'upload_file', 'upload_file': fp}, follow=True)
            self.assertRedirects(response, reverse('xasdb1:index'))
            self.assertContains(response, 'File uploaded')
        self.assertEqual(len(XASFile.objects.all()), len(self.xdi_files))

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
                response = self.c.post(reverse('xasdb1:upload'), {'name': 'upload_file', 'upload_file': fp}, follow=True)
            self.assertRedirects(response, reverse('xasdb1:index'))
            self.assertContains(response, 'File uploaded')
        self.assertEqual(len(XASFile.objects.all()), len(self.xdi_files))
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

    def test_element_Fe_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, 'No spectra found for Fe')
        # let's approve 3 of them and try again
        for obj in XASFile.objects.filter(atomic_number=26)[::2]:
            obj.review_status = XASFile.APPROVED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        #print(f'response: {response.content}')
        self.assertContains(response, '3 spectra found for Fe')

    def test_element_Zn_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Zn']))

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
                response = self.c.post(reverse('xasdb1:upload'), {'name': 'upload_file', 'upload_file': fp}, follow=True)
            self.assertRedirects(response, reverse('xasdb1:index'))
            self.assertContains(response, 'File uploaded')
        self.assertEqual(len(XASFile.objects.all()), len(self.xdi_files))
        # logout
        response = self.c.post(reverse('xasdb1:logout'))
        self.assertRedirects(response, reverse('xasdb1:index'))

    def test_element_no_files(self):
        # pretty sure there's no uranium data
        response = self.c.get(reverse('xasdb1:element', args=['U']))

    def test_element_Fe_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        self.assertContains(response, 'No spectra found for Fe')
        # let's approve 3 of them and try again
        for obj in XASFile.objects.filter(atomic_number=26)[::2]:
            obj.review_status = XASFile.APPROVED
            obj.save()
        response = self.c.get(reverse('xasdb1:element', args=['Fe']))
        #print(f'response: {response.content}')
        self.assertContains(response, '3 spectra found for Fe')

    def test_element_Zn_files(self):
        response = self.c.get(reverse('xasdb1:element', args=['Zn']))
        self.assertContains(response, 'No spectra found for Zn')
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
            response = self.c.post(reverse('xasdb1:upload'), {'name': 'upload_file', 'upload_file': fp}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'File uploaded')
        self.assertEqual(len(XASFile.objects.all()), 1)
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
            response = self.c.post(reverse('xasdb1:upload'), {'name': 'upload_file', 'upload_file': fp}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, 'File uploaded')
        self.assertEqual(len(XASFile.objects.all()), 1)
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

    def test_file_login_as_user(self):
        response = self.c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('xasdb1:index'))
        self.assertContains(response, USERNAME  + ' logged in!')
        file = XASFile.objects.all()[0]
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')
        file.review_status = XASFile.APPROVED
        file.save()
        response = self.c.post(reverse('xasdb1:file', args=[file.id]), follow=True)
        self.assertContains(response, f'Spectrum: {file.sample_name}')

    def test_file_login_as_admin(self):
        User.objects.create_superuser(username=2*USERNAME, password=2*PASSWORD, email='test@example.com')
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

