import pytest
from django.contrib.auth.models import AnonymousUser
from accounts.tests.factories import UserFactory
from unittest.mock import Mock

from core.permissions import CanManageCatalog

pytestmark = pytest.mark.django_db


# creates a staff, standard, or anonymous user to CanManageCatalog permission
@pytest.fixture
def dynamic_user(request):
    user_type = request.param
    if user_type == "staff":
        yield UserFactory(is_staff=True)
    elif user_type == "standard":
        yield UserFactory(is_staff=False)
    else:
        yield AnonymousUser()


@pytest.mark.describe("test the CanManageCatalog permission")
class TestManageCatalogPermission:
    @pytest.mark.parametrize(
        "dynamic_user, expected_result",
        [("staff", True), ("standard", False), ("anonymous", False)],
        indirect=["dynamic_user"],
    )
    @pytest.mark.it("returns True for a staff user")
    def test_has_permission(self, dynamic_user, expected_result):
        user = UserFactory(is_staff=True)
        request = Mock()
        request.user = dynamic_user
        view = Mock()

        permission = CanManageCatalog()

        assert permission.has_permission(request, view) == expected_result
