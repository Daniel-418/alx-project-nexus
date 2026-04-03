# type: ignore
import pytest
from django.urls import reverse
from products.tests.factories import OptionTypeFactory, OptionValueFactory
from core.tests.fixtures import staff_client, standard_user_client, anonymous_user

pytestmark = pytest.mark.django_db


@pytest.mark.describe("test the views available to option type")
class TestOptionValueFilter:
    @pytest.fixture
    def url(self):
        return reverse("option-value-list")

    @pytest.mark.it(
        "test that all option values are returned when you don't pass a filter in the url"
    )
    def test_no_filter_returns_all_option_values(self, staff_client, url):
        option_1 = OptionValueFactory()
        option_2 = OptionValueFactory()

        response = staff_client.get(url)

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 2

        ids = [item["id"] for item in data]

        assert option_1.id in ids
        assert option_2.id in ids

    @pytest.mark.it(
        "test that option values get filtered when specifying an option type in the url"
    )
    def test_option_type_filter_returns_only_its_option_values(self, staff_client, url):
        option_type = OptionTypeFactory()

        option_1 = OptionValueFactory()
        option_2 = OptionValueFactory()

        option_3 = OptionValueFactory(option_type=option_type)
        option_4 = OptionValueFactory(option_type=option_type)

        url = f"{url}?option_type={option_type.id}"
        response = staff_client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2

    @pytest.mark.it(
        "test that filtering by an option type with no values returns an empty list"
    )
    def test_option_type_filter_with_no_values_returns_empty_list(
        self, staff_client, url
    ):
        option_type = OptionTypeFactory()
        OptionValueFactory()  # belongs to a different option type

        url = f"{url}?option_type={option_type.id}"
        response = staff_client.get(url)

        assert response.status_code == 200
        assert response.json() == []
