from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):
    def test_signup_creates_user_and_redirects_to_login(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'newapplicant',
                'email': 'applicant@example.com',
                'password1': 'StrongPassword!42',
                'password2': 'StrongPassword!42',
            },
        )

        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newapplicant').exists())

    def test_login_and_logout(self):
        User.objects.create_user(username='applicant', password='StrongPassword!42')

        login_response = self.client.post(
            reverse('login'),
            {'username': 'applicant', 'password': 'StrongPassword!42'},
        )
        self.assertRedirects(login_response, reverse('home'), fetch_redirect_response=False)

        logout_response = self.client.post(reverse('logout'))
        self.assertRedirects(logout_response, reverse('login'))
