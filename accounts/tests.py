from django.contrib.auth.models import User
from django.test import TestCase
from .models import Profile


class ProfileTests(TestCase):
    def test_profile_created_for_new_user(self):
        user = User.objects.create_user(username='newuser', password='pass12345')
        self.assertEqual(user.profile.role, Profile.SEEKER)


class LoginRedirectTests(TestCase):
    def test_caretaker_login_redirects_to_caretaker_dashboard(self):
        user = User.objects.create_user(username='care', password='pass12345')
        user.profile.role = Profile.CARETAKER
        user.profile.approval_status = Profile.APPROVED
        user.profile.phone_verified = True
        user.profile.save()
        response = self.client.post('/login/', {'username': 'care', 'password': 'pass12345'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/caretaker/')

    def test_admin_login_redirects_to_platform_admin(self):
        user = User.objects.create_user(username='adminuser', password='pass12345', is_staff=True)
        user.profile.role = Profile.ADMIN
        user.profile.save()
        response = self.client.post('/login/', {'username': 'adminuser', 'password': 'pass12345'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/admin/')

    def test_seeker_login_redirects_to_saved_homes_dashboard(self):
        user = User.objects.create_user(username='seekeruser', password='pass12345')
        user.profile.role = Profile.SEEKER
        user.profile.approval_status = Profile.APPROVED
        user.profile.save()
        response = self.client.post('/login/', {'username': 'seekeruser', 'password': 'pass12345'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/account/')

    def test_seeker_signup_creates_seeker_profile(self):
        response = self.client.post('/seeker-signup/', {
            'username': 'newseeker',
            'email': 'newseeker@example.com',
            'phone': '0700000001',
            'password1': 'StrongPass12345',
            'password2': 'StrongPass12345',
        })
        self.assertEqual(response.status_code, 302)
        profile = User.objects.get(username='newseeker').profile
        self.assertEqual(profile.role, Profile.SEEKER)
        self.assertEqual(profile.phone, '0700000001')
