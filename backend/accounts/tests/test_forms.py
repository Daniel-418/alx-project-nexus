import unittest
from django.test import TestCase
from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.forms import UserCreationForm

User = get_user_model()


class UserCreationFormTest(TestCase):
    def test_form_valid_data(self):
        form = UserCreationForm(
            data={
                "email": "daniel@komolafe.com",
                "first_name": "daniel",
                "last_name": "komolafe",
                "password1": "first_password",
                "password2": "first_password",
            }
        )
        self.assertTrue(form.is_valid())

    def test_form_invalid_password_mismatch(self):
        """Test the form errors when passwords don't match"""
        form = UserCreationForm(
            data={
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "password1": "password123",
                "password2": "mismatch!!!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)
