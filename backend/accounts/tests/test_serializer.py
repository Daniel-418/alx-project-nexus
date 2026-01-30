from django.test import TestCase
from accounts.models import User
from accounts.serializers import CustomUserSerializerOutput


class CustomUserSerializer(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(  # pyright: ignore
            email="daniel@komolafe.dev",
            first_name="daniel",
            last_name="komolafe",
            password="password",
            phone_number="306-850-9733",
        )

    def test_correct_serializer_output(self):
        output = """{
            "id": 1,
            "email": "daniel@komolafe.dev",
            "first_name": "daniel",
            "last_name": "komolafe",
            "phone_number": "306-850-9733"
        }"""
