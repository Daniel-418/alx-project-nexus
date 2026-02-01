# type: ignore
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.tests.factories import UserFactory


class TestAuthenticationIntegration(APITestCase):
    """
    Integration Tests for JWT Authentication.
    These tests verify the full lifecycle: Login -> Get Token -> Use Token -> Access Data.
    """

    def setUp(self):
        # 1. Setup Data
        self.password = "strong_password_123"
        self.user = UserFactory(password=self.password)

        self.login_url = reverse("login")
        self.profile_url = reverse("profile")

    def test_full_auth_flow(self):
        """
        The Happy Path:
        User logs in with password.
        Server returns Access Token.
        User sends Access Token in Header.
        Server grants access to protected view.
        """
        login_payload = {"email": self.user.email, "password": self.password}
        login_response = self.client.post(self.login_url, login_payload)

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)

        access_token = login_response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        profile_response = self.client.get(self.profile_url)

        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["email"], self.user.email)

    def test_access_denied_without_token(self):
        """Test that requests with no header are rejected."""
        self.client.credentials()

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_denied_with_bad_token(self):
        """Test that garbage tokens are rejected."""
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid_junk_string")

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
