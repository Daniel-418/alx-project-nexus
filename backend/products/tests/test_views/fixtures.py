# type: ignore
import pytest
from rest_framework.test import APIClient as Client
from accounts.tests.factories import UserFactory
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

# enables database usage
pytestmark = pytest.mark.django_db


@pytest.fixture
def standard_user_client():
    client = Client()
    user = UserFactory()

    client.force_authenticate(user=user)
    client.user = user
    yield client


@pytest.fixture
def staff_client():
    client = Client()
    user = UserFactory(is_staff=True)

    client.force_authenticate(user=user)
    client.user = user
    yield client


@pytest.fixture
def anonymous_user():
    client = Client()
    user = AnonymousUser()

    client.user = user
    return client
