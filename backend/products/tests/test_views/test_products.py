# type: ignore
import uuid
import pytest
from products.tests.factories import ProductFactory
from django.urls import reverse

from products.models import Product, Variant, ProductImage
from products.tests.factories import VariantFactory, ProductImageFactory
from categories.tests.factories import CategoryFactory
from core.tests.fixtures import (
    staff_client,
    standard_user_client,
    anonymous_user,
    pytestmark,
)


@pytest.fixture
def create_url():
    return reverse("product-list")


@pytest.mark.describe("test the creating product using the viewset")
class TestProductCreate:
    @pytest.mark.it("test that a product can be created")
    def test_product_create(self, staff_client, create_url):
        request = {
            "name": "t-shirt",
            "price": "60",
            "description": "a brand new t-shirt",
        }
        response = staff_client.post(
            create_url, request, content_type="application/json"
        )

        assert Product.objects.filter(name="t-shirt").exists()
        assert response.status_code == 201
        assert "id" in response.json()
        assert "price" in response.json()
        assert "created_at" in response.json()
        assert "categories" in response.json()

    @pytest.mark.it("test that a product cannot be created by a non_staff user")
    def test_non_staff_cannot_create_product(self, standard_user_client, create_url):
        request = {
            "name": "t-shirt",
            "price": "60",
            "description": "a brand new t-shirt",
        }
        response = standard_user_client.post(
            create_url, request, content_type="application/json"
        )

        assert response.status_code == 403

    @pytest.mark.it("test that proper response for invalid request data")
    def test_bad_request_return_code_for_invalid_data(self, staff_client, create_url):
        request = {
            "name": "t-shirt",  # pyright: ignore
            "price": "invalid_price",
            "description": "a brand new t-shirt",
        }
        response = staff_client.post(
            create_url, request, content_type="application/json"
        )

        assert Product.objects.filter(name="t-shirt").exists() == False
        assert response.status_code == 400
        assert "price" in response.json()


@pytest.mark.describe("test the creating product using the viewset")
class TestProductList:
    @pytest.mark.it("test that different types of users can list products")
    @pytest.mark.parametrize(
        "user, expected_status",
        [("standard_user_client", 200), ("staff_client", 200), ("anonymous_user", 200)],
    )
    def test_product_list_by_an_different_users(
        self, user, expected_status, request, create_url
    ):

        ProductFactory()
        ProductFactory()
        client = request.getfixturevalue(user)
        response = client.get(create_url)
        data = response.json()

        assert response.status_code == 200
        assert len(data) == 2
        assert "variants" in data[0]


@pytest.mark.describe("test retrieving a single product using the viewset")
class TestProductRetrieve:
    @pytest.fixture
    def product(self):
        return ProductFactory()

    @pytest.fixture
    def detail_url(self, product):
        return reverse("product-detail", kwargs={"pk": product.id})

    @pytest.mark.it("test that any user type can retrieve a single product")
    @pytest.mark.parametrize(
        "user",
        ["staff_client", "standard_user_client", "anonymous_user"],
    )
    def test_any_user_can_retrieve_product(self, user, request, detail_url):
        client = request.getfixturevalue(user)
        response = client.get(detail_url)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "price" in data
        assert "variants" in data
        assert "created_at" in data

    @pytest.mark.it("test that a non-existent product returns 404")
    def test_non_existent_product_returns_404(self, anonymous_user):
        url = reverse("product-detail", kwargs={"pk": uuid.uuid4()})
        response = anonymous_user.get(url)
        assert response.status_code == 404


@pytest.mark.describe("test updating products using the viewset")
class TestProductUpdate:
    @pytest.mark.it(
        "test that an authorized user can update a product completely (PUT)"
    )
    def test_product_full_update(self, staff_client):
        product = ProductFactory(name="Old Shirt", price="20.00")

        url = reverse("product-detail", kwargs={"pk": product.id})

        update_data = {
            "name": "New Awesome Shirt",
            "price": "25.00",
            "description": "An updated description.",
        }
        response = staff_client.put(url, update_data, format="json")

        assert response.status_code == 200

        product.refresh_from_db()
        assert product.name == "New Awesome Shirt"
        assert float(product.price) == 25.00

        data = response.json()
        assert "id" in data
        assert "variants" in data

    @pytest.mark.it(
        "test that an authorized user can partially update a product (PATCH)"
    )
    def test_product_partial_update(self, staff_client):
        product = ProductFactory(name="Old Shirt", price="20.00")
        url = reverse("product-detail", kwargs={"pk": product.id})

        response = staff_client.patch(url, {"price": "99.99"}, format="json")

        assert response.status_code == 200
        product.refresh_from_db()

        assert product.name == "Old Shirt"
        assert float(product.price) == 99.99

    @pytest.mark.it("test that a non-staff user cannot update a product")
    def test_non_staff_cannot_update_product(self, standard_user_client):
        product = ProductFactory()
        url = reverse("product-detail", kwargs={"pk": product.id})
        response = standard_user_client.put(
            url,
            {"name": "Hacked", "price": "1.00", "description": "x"},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.it("test that an anonymous user cannot PUT or PATCH a product")
    @pytest.mark.parametrize("method", ["put", "patch"])
    def test_anonymous_cannot_update_product(self, anonymous_user, method):
        product = ProductFactory()
        url = reverse("product-detail", kwargs={"pk": product.id})
        response = getattr(anonymous_user, method)(
            url, {"name": "Hacked", "price": "1.00", "description": "x"}, format="json"
        )
        assert response.status_code in (401, 403)


@pytest.mark.describe("test deleting a product using the viewset")
class TestProductDestroy:
    @pytest.fixture
    def product(self):
        return ProductFactory()

    @pytest.fixture
    def detail_url(self, product):
        return reverse("product-detail", kwargs={"pk": product.id})

    @pytest.mark.it("test that a staff user can soft delete a product")
    def test_staff_can_delete_product(self, staff_client, product, detail_url):
        response = staff_client.delete(detail_url)

        assert response.status_code == 204
        fetched = Product.all_objects.get(pk=product.pk)
        assert fetched.deleted_at is not None

    @pytest.mark.it("test that a soft deleted product no longer appears in the list")
    def test_deleted_product_excluded_from_list(
        self, staff_client, product, detail_url, create_url
    ):
        staff_client.delete(detail_url)

        response = staff_client.get(create_url)
        ids = [p["id"] for p in response.json()]
        assert str(product.pk) not in ids

    @pytest.mark.it("test that a non-staff user cannot delete a product")
    def test_non_staff_cannot_delete_product(
        self, standard_user_client, product, detail_url
    ):
        response = standard_user_client.delete(detail_url)

        assert response.status_code == 403
        assert Product.objects.filter(pk=product.pk).exists()

    @pytest.mark.it("test that an anonymous user cannot delete a product")
    def test_anonymous_user_cannot_delete_product(
        self, anonymous_user, product, detail_url
    ):
        response = anonymous_user.delete(detail_url)

        assert response.status_code in (401, 403)
        assert Product.objects.filter(pk=product.pk).exists()

    @pytest.mark.it(
        "test that deleting a product cascades soft delete to variants and images"
    )
    def test_cascade_soft_delete_to_variants_and_images(
        self, staff_client, detail_url, product
    ):
        variant = VariantFactory(product=product)
        image = ProductImageFactory(product=product)

        staff_client.delete(detail_url)

        fetched_variant = Variant.all_objects.get(pk=variant.pk)
        fetched_image = ProductImage.all_objects.get(pk=image.pk)
        assert fetched_variant.deleted_at is not None
        assert fetched_image.deleted_at is not None


@pytest.mark.describe("test filtering products by category")
class TestProductFilterByCategory:
    @pytest.mark.it("test that products can be filtered by category")
    def test_filter_by_category(self, anonymous_user, create_url):
        cat = CategoryFactory()
        product_in = ProductFactory(categories=[cat])
        ProductFactory()

        response = anonymous_user.get(create_url, {"category": str(cat.id)})
        assert response.status_code == 200
        ids = [p["id"] for p in response.json()]
        assert str(product_in.id) in ids
        assert len(ids) == 1

    @pytest.mark.it("test that filtering by a non-existent category returns empty list")
    def test_filter_by_unknown_category_returns_empty(self, anonymous_user, create_url):
        ProductFactory()
        response = anonymous_user.get(create_url, {"category": str(uuid.uuid4())})
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.describe("test restroing a soft-deleted product via the viewset")
class TestProductRestore:
    @pytest.fixture
    def deleted_product(self):
        product = ProductFactory()
        product.delete()
        return product

    @pytest.fixture
    def restore_url(self, deleted_product):
        return reverse("product-restore", kwargs={"pk": deleted_product.id})

    @pytest.mark.it("test that a product can be deleted from the endpoint")
    def test_staff_can_delete_product(self, restore_url, deleted_product, staff_client):
        assert deleted_product.deleted_at is not None
        response = staff_client.post(restore_url)

        assert response.status_code == 200

        deleted_product.refresh_from_db()
        assert deleted_product.deleted_at is None

        assert Product.objects.filter(pk=deleted_product.id).exists()

    @pytest.mark.it("test that an authorized user cannot retore a product")
    @pytest.mark.parametrize(
        "client_type, expected_status",
        [("standard_user_client", 403), ("anonymous_user", 401)],
    )
    def test_unauthorized_user_cannot_restore(
        self, client_type, expected_status, request, deleted_product, restore_url
    ):
        client = request.getfixturevalue(client_type)

        response = client.post(restore_url)
        assert response.status_code == expected_status
        assert deleted_product.deleted_at is not None
