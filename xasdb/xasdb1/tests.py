from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

USERNAME = 'jpwqehfpfewpfhpfweq'
PASSWORD = 'wefooqewhfpwqhfp'

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
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD})
        #print(f"{response.content}")
        self.assertContains(response, 'Please enter a correct username and password. Note that both fields may be case-sensitive.')

    def test_success_login_from_view(self):
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD)
        c = Client()
        response = c.post(reverse('xasdb1:login'), {'username': USERNAME, 'password': PASSWORD})
        #print(f"{response.content}")
        self.assertRedirects(response, reverse('xasdb1:index'))

class UploadTests(TestCase):

    def setUp(self):
        pass
        self.user = User.objects.create_user(username=USERNAME, password=PASSWORD)
        login = self.client.login(username=USERNAME, password=PASSWORD)

    def test_nonexistent_file(self):
        pass

