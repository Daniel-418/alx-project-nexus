# type: ignore
from django.test import TestCase
from accounts.models import User
from accounts.serializers import (
    CustomUserSerializerOutput,
    CustomUserSerializerInput,
    LoginSerializer,
)
from accounts.tests.factories import UserFactory


class CustomUserSerializer(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_serializer_input(self):
        data = {
            "email": "daniel@adfadfa.dev",
            "password": "securepassword",
            "first_name": "test",
            "last_name": "user",
            "phone_number": "000-000",
        }

        serializer = CustomUserSerializerInput(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()
        output = serializer.data

        self.assertEqual(user.email, data["email"])
        self.assertNotEqual(user.password, data["password"])
        self.assertTrue(user.check_password("securepassword"))
        self.assertNotIn("password", output)
        self.assertIn("email", output)

    def test_input_required_fields(self):
        """Test that missing required fields trigger errors"""
        data = {"email": "incomplete@example.com", "password": "password"}
        serializer = CustomUserSerializerInput(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("first_name", serializer.errors)
        self.assertIn("last_name", serializer.errors)

    def test_serializer_output(self):
        serializer = CustomUserSerializerOutput(self.user)

        self.assertNotIn("password", serializer.data)


class LoginSerializerTest(TestCase):
    def setUp(self):
        self.password = "password"
        self.user = UserFactory(password=self.password)

    def test_serializer_output(self):
        data = {"email": self.user.email, "password": self.password}
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_password(self):
        data = {"email": self.user.email}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())

        self.assertIn("password", serializer.errors)
        error = serializer.errors["password"][0]
        self.assertEqual(error.code, "required")

    def test_missing_email(self):
        data = {"password": "daniel"}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())

        self.assertIn("email", serializer.errors)
        error = serializer.errors["email"][0]
        self.assertEqual(error.code, "required")

    def test_invalid_email_or_password(self):
        data = {"email": "randomemail@afa.com", "password": "randompassword"}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())

        self.assertIn("details", serializer.errors)

        self.assertIn("invalid email or password", str(serializer.errors))
