# type: ignore
from rest_framework.test import APIClient as Client
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from accounts.models import User
from accounts.tests.factories import UserFactory


class TestRegister(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("register")

    def test_correct_input_and_output(self):
        """
        Ensure we can register a new user with valid data.
        """
        request = {
            "email": "daniel@aadfasd.com",
            "password": "afadfadf",
            "first_name": "daniel",
            "last_name": "komolafe",
            "phone_number": "2343243234",
        }
        response = self.client.post(self.url, request, content_type="application/json")

        # Check the user was created
        self.assertTrue(User.objects.filter(first_name="daniel").exists())

        # Check for the right response for a successfully created user
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["user"]["first_name"], "daniel")
        self.assertEqual(response.json()["user"]["last_name"], "komolafe")
        self.assertIn("refresh", response.json())
        self.assertIn("access", response.json())

    def test_unallowed_methods(self):
        """
        Ensure other methods are not allowed
        """
        response_get = self.client.get(self.url)
        response_put = self.client.put(self.url)
        self.assertEqual(response_get.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unwritable_fields(self):
        """
        Ensure sensitive fields cannot be set during registration
        The Api should ignore sensitive fields that arre set and create a standard user instead.
        """
        request = {
            "id": 50,
            "email": "daniel@aadfasd.com",
            "password": "afadfadf",
            "first_name": "daniel",
            "last_name": "komolafe",
            "phone_number": "2343243234",
            "is_staff": True,
            "is_superuser": True,
        }
        response = self.client.post(self.url, request, content_type="application/json")
        self.assertEqual(response.status_code, 201)

        user = User.objects.get(email="daniel@aadfasd.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotEqual(request["id"], str(user.id))

    def test_registering_an_existing_user(self):
        """
        Ensure user cannot register with an email that already exists
        """
        user = UserFactory()
        request = {
            "email": user.email,
            "first_name": "daniel",
            "phone_number": "2343243234",
        }
        response = self.client.post(self.url, request, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())
        self.assertEqual(
            "user with this email already exists.", response.json()["email"][0]
        )
        self.assertIn("last_name", response.json())
        self.assertIn("password", response.json())

    def test_password_hashing_security(self):
        """
        - Ensure the raw password is NOT stored in the database.
        - Ensure the stored password is a valid hash of the raw password.
        """
        raw_password = "complex_password_123!"
        user_data = UserFactory.build()

        payload = {
            "email": user_data.email,
            "password": raw_password,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "phone_number": "1234567890",
        }

        self.client.post(self.url, payload)

        user = User.objects.get(email=user_data.email)

        self.assertNotEqual(
            user.password,
            raw_password,
            "Security Breach: Password is stored in plain text!",
        )

        self.assertTrue(
            user.check_password(raw_password),
            "Security Error: The stored hash does not match the provided password.",
        )


class TestLogin(TestCase):
    """
    Tests the login view
    """

    def setUp(self):
        self.client = Client()
        self.url = reverse("login")

        self.password = "strong_password_123"
        self.user = UserFactory(email="example@example.com")
        self.user.set_password(self.password)
        self.user.save()

        self.payload = {"email": "example@example.com", "password": self.password}

    def test_correct_output(self):
        """
        Happy path: tests that a user can login correctly
        """
        response = self.client.post(self.url, self.payload)

        self.assertIn("refresh", response.json())
        self.assertIn("access", response.json())
        self.assertTrue(len(response.json()["refresh"]) > 0)
        self.assertTrue(len(response.json()["access"]) > 0)
        self.assertEqual(response.json()["message"], "login successful")

        user = User.objects.get(email=self.payload["email"])
        self.assertTrue(user.is_authenticated)

    def test_login_failure(self):
        """
        Tests that the api fails gracefully when a login fails.
        """
        payload = {"email": "wrong@example.com", "password": "wrong"}
        response = self.client.post(self.url, payload)

        self.assertIn(response.status_code, [400, 401])

        data = response.json()
        self.assertIn("details", data)
        self.assertEqual("invalid email or password", data["details"][0])


class Test_User_profile(TestCase):
    """
    Tests that a User profile returns the correct value
    """

    def setUp(self):
        self.client = Client()
        self.url = reverse("profile")
        self.password = "password"
        self.user = UserFactory(password=self.password)

        self.client.force_authenticate(user=self.user)

    def test_correct_output(self):
        """
        Test that a logged in user can retrieve their profile information
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("id", data)
        self.assertIn("first_name", data)
        self.assertIn("last_name", data)
        self.assertIn("email", data)
        self.assertNotIn("password", data)
        self.assertIn("phone_number", data)

        self.assertEqual(data["id"], str(self.user.id))
        self.assertEqual(data["email"], self.user.email)

    def test_unauthenticated_access_is_denied(self):
        self.client.logout()
        self.client.credentials()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
