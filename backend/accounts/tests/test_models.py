import unittest
from django.test import TestCase
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(  # pyright: ignore
            email="example@example.com", first_name="Daniel", last_name="Komolafe"
        )
        self.assertTrue(User.objects.filter(email="example@example.com").exists())
        self.assertEqual(user.email, "example@example.com")
        self.assertEqual(user.first_name, "Daniel")
        self.assertEqual(user.last_name, "Komolafe")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(str(user), "Daniel: example@example.com")

    def test_create_user_without_required_fields(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(  # pyright: ignore
                email="", first_name="Test", last_name="user", password="foo"
            )
        with self.assertRaises(ValueError):
            User.objects.create_user(  # pyright: ignore
                email="daniel@komolafe.com",
                first_name="",
                last_name="user",
                password="foo",
            )
        with self.assertRaises(ValueError):
            User.objects.create_user(  # pyright: ignore
                email="daniel@komolafe.com",
                first_name="Test",
                last_name="",
                password="foo",
            )

    def test_create_superuser(self):
        user = User.objects.create_superuser(  # pyright: ignore
            email="komolafe@daniel.com",
            password="test",
            first_name="test",
            last_name="test",
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertEqual(user.email, "komolafe@daniel.com")
        self.assertTrue(user.is_active)
