# type: ignore
from products.models import Variant
import pytest
from django.urls import reverse
from products.serializers import VariantOutputSerializer
from products.tests.factories import (
    OptionValueFactory,
    ProductFactory,
    ProductImageFactory,
    VariantFactory,
)
from core.tests.fixtures import (
    staff_client,
    standard_user_client,
    anonymous_user,
    pytestmark,
)


@pytest.fixture
def product():
    return ProductFactory()


@pytest.fixture
def image(product):
    return ProductImageFactory(product=product)


@pytest.fixture
def option_value():
    return OptionValueFactory()


@pytest.fixture
def create_url(product):
    url = reverse("product-variants-list", kwargs={"product_pk": product.id})
    return url


@pytest.mark.describe("test that a variant can be created")
class TestVariantCreation:
    @pytest.mark.it("test that a variant can be created")
    def test_that_a_variant_can_be_created(
        self, staff_client, create_url, product, image, option_value
    ):
        request = {
            "price": "50",
            "stock": 0,
            "images": [str(image.id)],
            "sku": "1234-pser",
            "is_master": False,
            "option_values": [str(option_value.id)],
        }
        response = staff_client.post(
            create_url, request, content_type="application/json"
        )
        data = response.json()

        assert response.status_code == 201, data

        variant = Variant.objects.get(sku="1234-pser")
        assert variant.product == product
        assert image in variant.images.all()
        assert option_value in variant.option_values.all()


@pytest.mark.describe("test listing variants")
class TestVariantList:
    @pytest.mark.it("test that a non-staff user cannot create a variant")
    def test_non_staff_cannot_create_variant(
        self, standard_user_client, create_url, image, option_value
    ):
        request = {
            "price": "50",
            "stock": 0,
            "images": [str(image.id)],
            "sku": "non-staff-sku",
            "is_master": False,
            "option_values": [str(option_value.id)],
        }
        response = standard_user_client.post(
            create_url, request, content_type="application/json"
        )
        assert response.status_code == 403

    @pytest.mark.it("test that an anonymous user cannot create a variant")
    def test_anonymous_cannot_create_variant(
        self, anonymous_user, create_url, image, option_value
    ):
        request = {
            "price": "50",
            "stock": 0,
            "images": [str(image.id)],
            "sku": "anon-sku",
            "is_master": False,
            "option_values": [str(option_value.id)],
        }
        response = anonymous_user.post(
            create_url, request, content_type="application/json"
        )
        assert response.status_code in (401, 403)

    @pytest.mark.it("test that missing required fields return 400 with field errors")
    def test_invalid_data_returns_400(self, staff_client, create_url):
        # sku is required — omitting it should produce a 400 with an error on "sku"
        response = staff_client.post(
            create_url, {"price": "50", "stock": 0}, content_type="application/json"
        )
        assert response.status_code == 400
        assert "sku" in response.json()

    @pytest.mark.it("test that a non-existent product_pk returns 404")
    def test_non_existent_product_returns_404(self, staff_client):
        import uuid

        url = reverse("product-variants-list", kwargs={"product_pk": uuid.uuid4()})
        response = staff_client.post(
            url,
            {"price": "50", "stock": 0, "sku": "x"},
            content_type="application/json",
        )
        assert response.status_code == 404

    @pytest.mark.it("ensures get_queryset only returns variants for the URL product")
    def test_get_queryset_filters_by_product_id(self, standard_user_client):
        target_product = ProductFactory()
        decoy_product = ProductFactory()

        target_variant_1 = VariantFactory(product=target_product)
        target_variant_2 = VariantFactory(product=target_product)

        decoy_variant = VariantFactory(product=decoy_product)

        list_url = reverse(
            "product-variants-list", kwargs={"product_pk": target_product.id}
        )

        response = standard_user_client.get(list_url)
        data = response.json()

        assert response.status_code == 200

        assert len(data) == 2

        returned_ids = [item["id"] for item in data]

        assert str(target_variant_1.id) in returned_ids
        assert str(target_variant_2.id) in returned_ids

        assert str(decoy_variant.id) not in returned_ids


@pytest.mark.describe("test retrieving a single variant using the viewset")
class TestVariantRetrieve:
    @pytest.fixture
    def variant(self, product):
        return VariantFactory(product=product)

    @pytest.fixture
    def detail_url(self, product, variant):
        return reverse(
            "product-variants-detail",
            kwargs={"product_pk": product.id, "pk": variant.id},
        )

    @pytest.mark.it("test that any user type can retrieve a single variant")
    @pytest.mark.parametrize(
        "user", ["staff_client", "standard_user_client", "anonymous_user"]
    )
    def test_any_user_can_retrieve_variant(self, user, request, detail_url):
        client = request.getfixturevalue(user)
        response = client.get(detail_url)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "sku" in data
        assert "price" in data
        assert "stock" in data

    @pytest.mark.it("test that a non-existent variant returns 404")
    def test_non_existent_variant_returns_404(self, anonymous_user, product):
        import uuid

        url = reverse(
            "product-variants-detail",
            kwargs={"product_pk": product.id, "pk": uuid.uuid4()},
        )
        response = anonymous_user.get(url)
        assert response.status_code == 404


@pytest.mark.describe("test updating a variant using the viewset")
class TestVariantUpdate:
    @pytest.fixture
    def variant(self, product):
        return VariantFactory(product=product)

    @pytest.fixture
    def detail_url(self, product, variant):
        return reverse(
            "product-variants-detail",
            kwargs={"product_pk": product.id, "pk": variant.id},
        )

    def test_staff_can_fully_update_variant(
        self, staff_client, detail_url, product, variant
    ):
        data = {"price": "50", "sku": "LAPPIE"}
        assert Variant.objects.filter(id=variant.id).exists()
        response = staff_client.put(detail_url, data)
        assert response.status_code == 200
        response_data = response.json()

        assert str(variant.id) == response_data["id"]

        variant.refresh_from_db()
        assert variant.price == 50
        assert variant.sku == "LAPPIE"

    def test_staff_can_partially_update_variant(
        self, staff_client, detail_url, product, variant
    ):
        data = {"price": "50"}
        sku = str(variant.sku)
        assert Variant.objects.filter(id=variant.id).exists()
        response = staff_client.patch(detail_url, data)
        assert response.status_code == 200

        response_data = response.json()
        assert str(variant.id) == response_data["id"]

        variant.refresh_from_db()
        assert variant.price == 50
        assert variant.sku == sku

    @pytest.mark.parametrize(
        "client, expected_output",
        [
            ("staff_client", 200),
            ("standard_user_client", 403),
            ("anonymous_user", 401),
        ],
    )
    def test_non_staff_cannot_update_variant(
        self, client, expected_output, request, variant, detail_url
    ):
        data = {"price": "50", "sku": "LAPPIE"}
        client = request.getfixturevalue(client)
        response = client.put(detail_url, data)
        response_data = response.json()

        assert response.status_code == expected_output


@pytest.mark.describe("test deleting a variant using the viewset")
class TestVariantDestroy:
    @pytest.fixture
    def variant(self, product):
        return VariantFactory(product=product)

    @pytest.fixture
    def detail_url(self, product, variant):
        return reverse(
            "product-variants-detail",
            kwargs={"product_pk": product.id, "pk": variant.id},
        )

    @pytest.fixture
    def list_url(self, product):
        return reverse("product-variants-list", kwargs={"product_pk": product.id})

    @pytest.mark.it("test that a staff user can soft-delete a variant")
    def test_staff_can_delete_variant(self, staff_client, variant, detail_url):
        response = staff_client.delete(detail_url)
        assert response.status_code == 204
        fetched = Variant.all_objects.get(pk=variant.pk)
        assert fetched.deleted_at is not None

    @pytest.mark.it("test that a soft-deleted variant is excluded from the list")
    def test_deleted_variant_excluded_from_list(
        self, staff_client, variant, detail_url, list_url
    ):
        staff_client.delete(detail_url)
        response = staff_client.get(list_url)
        ids = [v["id"] for v in response.json()]
        assert str(variant.pk) not in ids

    @pytest.mark.it("test that a non-staff user cannot delete a variant")
    def test_non_staff_cannot_delete_variant(
        self, standard_user_client, variant, detail_url
    ):
        response = standard_user_client.delete(detail_url)
        assert response.status_code == 403
        assert Variant.objects.filter(pk=variant.pk).exists()

    @pytest.mark.it("test that an anonymous user cannot delete a variant")
    def test_anonymous_cannot_delete_variant(self, anonymous_user, variant, detail_url):
        response = anonymous_user.delete(detail_url)
        assert response.status_code in (401, 403)
        assert Variant.objects.filter(pk=variant.pk).exists()


@pytest.mark.describe("test restoring a soft-deleted variant via the viewset")
class TestVariantRestore:
    @pytest.fixture
    def deleted_variant(self, product):
        variant = VariantFactory(product=product)
        variant.delete()
        return variant

    @pytest.fixture
    def restore_url(self, product, deleted_variant):
        return reverse(
            "product-variants-restore",
            kwargs={"product_pk": product.id, "pk": deleted_variant.id},
        )

    @pytest.mark.it("test that a staff user can restore a soft-deleted variant")
    def test_staff_can_restore_variant(
        self, staff_client, deleted_variant, restore_url
    ):
        assert deleted_variant.deleted_at is not None
        response = staff_client.post(restore_url)
        assert response.status_code == 200
        deleted_variant.refresh_from_db()
        assert deleted_variant.deleted_at is None
        assert Variant.objects.filter(pk=deleted_variant.pk).exists()

    @pytest.mark.it("test that unauthorized users cannot restore a variant")
    @pytest.mark.parametrize(
        "client_type, expected_status",
        [("standard_user_client", 403), ("anonymous_user", 401)],
    )
    def test_unauthorized_user_cannot_restore(
        self, client_type, expected_status, request, deleted_variant, restore_url
    ):
        client = request.getfixturevalue(client_type)
        response = client.post(restore_url)
        assert response.status_code == expected_status
        deleted_variant.refresh_from_db()
        assert deleted_variant.deleted_at is not None


@pytest.mark.describe(
    "test adding/removing images from a variant via the images action"
)
class TestVariantImageManagement:
    @pytest.fixture
    def variant(self, product):
        return VariantFactory(product=product, images=[])

    @pytest.fixture
    def own_image(self, product):
        return ProductImageFactory(product=product)

    @pytest.fixture
    def foreign_image(self):
        other_product = ProductFactory()
        return ProductImageFactory(product=other_product)

    @pytest.fixture
    def images_url(self, product, variant):
        return reverse(
            "product-variants-images",
            kwargs={"product_pk": product.id, "pk": variant.id},
        )

    @pytest.mark.it("staff can add an image belonging to the same product")
    def test_staff_can_add_own_image(
        self, staff_client, images_url, variant, own_image
    ):
        response = staff_client.post(
            images_url, {"images": [str(own_image.id)]}, content_type="application/json"
        )
        assert response.status_code == 200, response.json()
        variant.refresh_from_db()
        assert own_image in variant.images.all()

    @pytest.mark.it("staff can remove an image from a variant")
    def test_staff_can_remove_image(self, staff_client, images_url, variant, own_image):
        variant.images.add(own_image)
        response = staff_client.delete(
            images_url, {"images": [str(own_image.id)]}, content_type="application/json"
        )
        assert response.status_code == 200, response.json()
        variant.refresh_from_db()
        assert own_image not in variant.images.all()

    @pytest.mark.it("adding an image from a different product returns 400")
    def test_foreign_image_rejected(self, staff_client, images_url, foreign_image):
        response = staff_client.post(
            images_url,
            {"images": [str(foreign_image.id)]},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "images" in response.json()

    @pytest.mark.it("non-staff cannot add images")
    def test_non_staff_cannot_add_images(
        self, standard_user_client, images_url, own_image
    ):
        response = standard_user_client.post(
            images_url, {"images": [str(own_image.id)]}, content_type="application/json"
        )
        assert response.status_code == 403

    @pytest.mark.it("anonymous user cannot add images")
    def test_anonymous_cannot_add_images(self, anonymous_user, images_url, own_image):
        response = anonymous_user.post(
            images_url, {"images": [str(own_image.id)]}, content_type="application/json"
        )
        assert response.status_code in (401, 403)


@pytest.mark.describe("test image ownership validation on variant create/update")
class TestVariantImageOwnershipOnWrite:
    @pytest.mark.it(
        "creating a variant with an image from a different product returns 400"
    )
    def test_create_variant_with_foreign_image_returns_400(self, staff_client, product):
        other_product = ProductFactory()
        foreign_image = ProductImageFactory(product=other_product)

        url = reverse("product-variants-list", kwargs={"product_pk": product.id})
        data = {
            "price": "50",
            "stock": 0,
            "images": [str(foreign_image.id)],
            "sku": "FOREIGN-IMG-SKU",
            "is_master": False,
            "option_values": [],
        }
        response = staff_client.post(url, data, content_type="application/json")
        assert response.status_code == 400
        assert "images" in response.json()

    @pytest.mark.it(
        "updating a variant with an image from a different product returns 400"
    )
    def test_update_variant_with_foreign_image_returns_400(self, staff_client, product):
        variant = VariantFactory(product=product, images=[])
        other_product = ProductFactory()
        foreign_image = ProductImageFactory(product=other_product)

        url = reverse(
            "product-variants-detail",
            kwargs={"product_pk": product.id, "pk": variant.id},
        )
        response = staff_client.patch(
            url,
            {"images": [str(foreign_image.id)]},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "images" in response.json()
