from datetime import timedelta
import unittest
import uuid
from django.test import TestCase
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.tests.factories import UserFactory


User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_with_required_fields(self):
        user = UserFactory(  # pyright: ignore
            email="example@example.com",
            first_name="Daniel",
            last_name="Komolafe",
            phone_number="306-850-9733",
        )
        self.assertTrue(User.objects.filter(email="example@example.com").exists())
        self.assertEqual(user.email, "example@example.com")
        self.assertEqual(user.first_name, "Daniel")
        self.assertEqual(user.last_name, "Komolafe")
        self.assertEqual(user.phone_number, "306-850-9733")
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

    def test_user_id_field(self):
        user = UserFactory()
        uuid_string = str(user.id)
        fetched_user = User.objects.get(id=uuid_string)
        user_b = UserFactory()

        self.assertIsNotNone(user.id)
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.id.version, 4)
        self.assertNotEqual(user.id, user_b.id)
        self.assertEqual(fetched_user, user)

    def test_created_at_field(self):
        user = UserFactory()

        self.assertIsNotNone(user.created_at)
        self.assertAlmostEqual(
            user.created_at, timezone.now(), delta=timedelta(seconds=1)
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

    def test_create_superuser_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(  # pyright: ignore
                email="komolafe@daniel.com",
                password="test",
                first_name="test",
                last_name="test",
                is_staff=False,
            )
        with self.assertRaises(ValueError):
            User.objects.create_superuser(  # pyright: ignore
                email="komolafe@daniel.com",
                password="test",
                first_name="test",
                last_name="test",
                is_superuser=False,
            )
