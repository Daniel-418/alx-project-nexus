import uuid
import pytest
from django.urls import reverse
from categories.models import Category
from categories.tests.factories import CategoryFactory
from core.tests.fixtures import staff_client, anonymous_user, pytestmark


@pytest.fixture
def create_url():
    return reverse("category-list")


@pytest.mark.describe("test creating a category using the viewset")
class TestCategoryCreate:
    @pytest.mark.it("test that a category can be created")
    def test_category_create(self, staff_client, create_url):
        request = {"name": "men", "description": "Category to contain all of the men"}
        response = staff_client.post(create_url, request, content_type="application/json")

        assert response.status_code == 201, response.json()
        assert Category.objects.filter(name=request["name"]).exists()
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "description" in data

    @pytest.mark.it("test that a category can be created with a parent")
    def test_category_create_with_parent(self, staff_client, create_url):
        parent = CategoryFactory()
        request = {"name": "shirts", "description": "Shirts for men", "parent": str(parent.id)}
        response = staff_client.post(create_url, request, content_type="application/json")

        assert response.status_code == 201
        child = Category.objects.get(name="shirts")
        assert child.parent == parent


@pytest.mark.describe("test listing categories using the viewset")
class TestCategoryList:
    @pytest.mark.it("test that categories are listed correctly")
    def test_list_returns_all_categories(self, anonymous_user, create_url):
        CategoryFactory()
        CategoryFactory()
        response = anonymous_user.get(create_url)

        assert response.status_code == 200
        assert len(response.json()) == 2


@pytest.mark.describe("test retrieving a single category using the viewset")
class TestCategoryRetrieve:
    @pytest.fixture
    def category(self):
        return CategoryFactory()

    @pytest.fixture
    def detail_url(self, category):
        return reverse("category-detail", kwargs={"pk": category.id})

    @pytest.mark.it("test that a category can be retrieved")
    def test_retrieve_category(self, anonymous_user, detail_url, category):
        response = anonymous_user.get(detail_url)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(category.id)
        assert data["name"] == category.name
        assert "description" in data

    @pytest.mark.it("test that a non-existent category returns 404")
    def test_non_existent_returns_404(self, anonymous_user):
        url = reverse("category-detail", kwargs={"pk": uuid.uuid4()})
        response = anonymous_user.get(url)
        assert response.status_code == 404


@pytest.mark.describe("test updating a category using the viewset")
class TestCategoryUpdate:
    @pytest.fixture
    def category(self):
        return CategoryFactory(name="Old Name", description="Old desc")

    @pytest.fixture
    def detail_url(self, category):
        return reverse("category-detail", kwargs={"pk": category.id})

    @pytest.mark.it("test that a category can be fully updated (PUT)")
    def test_full_update(self, staff_client, category, detail_url):
        response = staff_client.put(
            detail_url, {"name": "New Name", "description": "New desc"}, format="json"
        )
        assert response.status_code == 200
        category.refresh_from_db()
        assert category.name == "New Name"
        assert category.description == "New desc"

    @pytest.mark.it("test that a category can be partially updated (PATCH)")
    def test_partial_update(self, staff_client, category, detail_url):
        response = staff_client.patch(detail_url, {"name": "Patched"}, format="json")
        assert response.status_code == 200
        category.refresh_from_db()
        assert category.name == "Patched"
        assert category.description == "Old desc"


@pytest.mark.describe("test deleting a category using the viewset")
class TestCategoryDestroy:
    @pytest.fixture
    def category(self):
        return CategoryFactory()

    @pytest.fixture
    def detail_url(self, category):
        return reverse("category-detail", kwargs={"pk": category.id})

    @pytest.mark.it("test that a staff user can delete a category")
    def test_staff_can_delete(self, staff_client, category, detail_url):
        response = staff_client.delete(detail_url)
        assert response.status_code == 204
        assert not Category.objects.filter(pk=category.pk).exists()
