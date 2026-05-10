from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SuperuserAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username='superadmin',
            email='superadmin@example.com',
            password='pass12345',
        )

    def test_superuser_is_app_admin_even_with_default_role(self):
        self.assertEqual(self.superuser.role, 'inspector')
        self.assertTrue(self.superuser.is_superuser)
        self.assertTrue(self.superuser.is_admin)

    def test_superuser_uses_admin_dashboard_flow(self):
        self.client.login(username='superadmin', password='pass12345')

        response = self.client.get(reverse('role_redirect'))
        self.assertRedirects(response, reverse('dashboard'))

        response = self.client.get(reverse('inspector_dashboard'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_superuser_can_open_user_management(self):
        self.client.login(username='superadmin', password='pass12345')

        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')
