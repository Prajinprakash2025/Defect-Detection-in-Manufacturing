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

    def test_superuser_can_create_and_delete_user_from_user_management(self):
        User = get_user_model()
        self.client.login(username='superadmin', password='pass12345')

        response = self.client.post(reverse('user_management'), {
            'action': 'create',
            'username': 'line_inspector',
            'email': 'line@example.com',
            'password': 'pass12345',
            'role': 'inspector',
            'active': 'on',
        })
        self.assertRedirects(response, reverse('user_management'))
        created_user = User.objects.get(username='line_inspector')
        self.assertEqual(created_user.role, 'inspector')
        self.assertTrue(created_user.is_active)

        response = self.client.post(reverse('delete_managed_user', args=[created_user.pk]))
        self.assertRedirects(response, reverse('user_management'))
        self.assertFalse(User.objects.filter(username='line_inspector').exists())

    def test_superuser_can_update_user_password_from_user_management(self):
        User = get_user_model()
        managed_user = User.objects.create_user(
            username='line_inspector',
            email='line@example.com',
            password='oldpass123',
            role='inspector',
        )
        self.client.login(username='superadmin', password='pass12345')

        response = self.client.post(reverse('update_managed_user_info', args=[managed_user.pk]), {
            'username': 'line_inspector',
            'email': 'line@example.com',
            'password': 'newpass123',
            'confirm_password': 'newpass123',
        })

        self.assertRedirects(response, reverse('user_management'))
        managed_user.refresh_from_db()
        self.assertTrue(managed_user.check_password('newpass123'))

    def test_admin_user_role_is_protected_in_user_management(self):
        User = get_user_model()
        admin_user = User.objects.create_user(
            username='plant_admin',
            email='plant@example.com',
            password='adminpass123',
            role='admin',
        )
        self.client.login(username='superadmin', password='pass12345')

        response = self.client.post(reverse('change_user_role', args=[admin_user.pk]), {
            'role': 'inspector',
        })

        self.assertRedirects(response, reverse('user_management'))
        admin_user.refresh_from_db()
        self.assertEqual(admin_user.role, 'admin')
