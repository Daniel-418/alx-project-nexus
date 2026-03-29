# type: ignore
import base64
import uuid
from django.core.files.uploadedfile import SimpleUploadedFile
import pytest
from django.urls import reverse
from products.models import ProductImage
from products.tests.factories import ProductImageFactory, ProductFactory
from products.tests.test_views.fixtures import staff_client, pytestmark

_B64_IMG = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="


@pytest.fixture
def product():
    return ProductFactory()


@pytest.fixture
def existing_image(product):
    return ProductImageFactory(product=product)


@pytest.fixture
def image_file():
    return SimpleUploadedFile(
        name="test_image.jpg",
        content_type="image/jpeg",
        content=base64.b64decode(_B64_IMG),
    )


@pytest.fixture
def create_url(product):
    return reverse("product-images-list", kwargs={"product_pk": product.id})


@pytest.mark.describe("test that a product image can be created")
class TestProductImageCreation:
    @pytest.mark.it("staff can create an image and product is set from URL")
    def test_staff_can_create_image(
        self, staff_client, create_url, product, image_file
    ):
        request = {
            "image": image_file,
            "alt_text": "a blue square",
            "is_feature": False,
        }
        response = staff_client.post(create_url, request)
        assert response.status_code == 201, response.json()

        data = response.json()
        db_image = ProductImage.objects.get(id=data["id"])
        assert db_image.product == product
        assert db_image.alt_text == "a blue square"

    @pytest.mark.it("display_order is auto-set when not provided")
    def test_display_order_auto_set(self, staff_client, create_url, image_file):
        response = staff_client.post(
            create_url, {"image": image_file, "alt_text": "auto order"}
        )
        assert response.status_code == 201, response.json()
        assert response.json()["display_order"] is not None

    @pytest.mark.it("non-existent product_pk returns 404")
    def test_non_existent_product_returns_404(self, staff_client, image_file):
        url = reverse("product-images-list", kwargs={"product_pk": uuid.uuid4()})
        response = staff_client.post(url, {"image": image_file, "alt_text": "x"})
        assert response.status_code == 404

    @pytest.mark.it("missing required field returns 400 with field error")
    def test_missing_alt_text_returns_400(self, staff_client, create_url, image_file):
        response = staff_client.post(create_url, {"image": image_file})
        assert response.status_code == 400
        assert "alt_text" in response.json()


@pytest.mark.describe("test listing product images")
class TestProductImageList:
    @pytest.mark.it("queryset is filtered to the URL product only")
    def test_list_filtered_by_product(self, staff_client):
        target = ProductFactory()
        decoy = ProductFactory()

        img1 = ProductImageFactory(product=target)
        img2 = ProductImageFactory(product=target)
        decoy_img = ProductImageFactory(product=decoy)

        url = reverse("product-images-list", kwargs={"product_pk": target.id})
        response = staff_client.get(url)
        assert response.status_code == 200

        ids = [item["id"] for item in response.json()]
        assert str(img1.id) in ids
        assert str(img2.id) in ids
        assert str(decoy_img.id) not in ids

    @pytest.mark.it("soft-deleted images are excluded from the list")
    def test_deleted_image_excluded_from_list(
        self, staff_client, product, existing_image
    ):
        existing_image.delete()
        url = reverse("product-images-list", kwargs={"product_pk": product.id})
        response = staff_client.get(url)
        ids = [item["id"] for item in response.json()]
        assert str(existing_image.id) not in ids


@pytest.mark.describe("test retrieving a single product image")
class TestProductImageRetrieve:
    @pytest.mark.it("non-existent image pk returns 404")
    def test_non_existent_image_returns_404(self, staff_client, product):
        url = reverse(
            "product-images-detail",
            kwargs={"product_pk": product.id, "pk": uuid.uuid4()},
        )
        response = staff_client.get(url)
        assert response.status_code == 404


@pytest.mark.describe("test updating a product image")
class TestProductImageUpdate:
    @pytest.fixture
    def detail_url(self, product, existing_image):
        return reverse(
            "product-images-detail",
            kwargs={"product_pk": product.id, "pk": existing_image.id},
        )

    @pytest.mark.it("staff can fully update an image")
    def test_staff_can_fully_update(
        self, staff_client, detail_url, existing_image, image_file
    ):
        data = {"image": image_file, "alt_text": "updated alt", "is_feature": True}
        response = staff_client.put(detail_url, data)
        assert response.status_code == 200
        existing_image.refresh_from_db()
        assert existing_image.alt_text == "updated alt"
        assert existing_image.is_feature is True

    @pytest.mark.it("staff can partially update an image")
    def test_staff_can_partially_update(self, staff_client, detail_url, existing_image):
        original_alt = existing_image.alt_text
        response = staff_client.patch(detail_url, {"is_feature": True})
        assert response.status_code == 200
        existing_image.refresh_from_db()
        assert existing_image.is_feature is True
        assert existing_image.alt_text == original_alt


@pytest.mark.describe("test deleting a product image")
class TestProductImageDestroy:
    @pytest.fixture
    def detail_url(self, product, existing_image):
        return reverse(
            "product-images-detail",
            kwargs={"product_pk": product.id, "pk": existing_image.id},
        )

    @pytest.fixture
    def list_url(self, product):
        return reverse("product-images-list", kwargs={"product_pk": product.id})

    @pytest.mark.it("staff can soft-delete an image")
    def test_staff_can_delete_image(self, staff_client, existing_image, detail_url):
        response = staff_client.delete(detail_url)
        assert response.status_code == 204
        fetched = ProductImage.all_objects.get(pk=existing_image.pk)
        assert fetched.deleted_at is not None

    @pytest.mark.it("soft-deleted image is excluded from the list")
    def test_deleted_image_excluded_from_list(
        self, staff_client, existing_image, detail_url, list_url
    ):
        staff_client.delete(detail_url)
        response = staff_client.get(list_url)
        ids = [item["id"] for item in response.json()]
        assert str(existing_image.pk) not in ids


@pytest.mark.describe("test restoring a soft-deleted product image")
class TestProductImageRestore:
    @pytest.fixture
    def deleted_image(self, product):
        img = ProductImageFactory(product=product)
        img.delete()
        return img

    @pytest.fixture
    def restore_url(self, product, deleted_image):
        return reverse(
            "product-images-restore",
            kwargs={"product_pk": product.id, "pk": deleted_image.id},
        )

    @pytest.mark.it("staff can restore a soft-deleted image")
    def test_staff_can_restore_image(self, staff_client, deleted_image, restore_url):
        assert deleted_image.deleted_at is not None
        response = staff_client.post(restore_url)
        assert response.status_code == 200
        deleted_image.refresh_from_db()
        assert deleted_image.deleted_at is None
        assert ProductImage.objects.filter(pk=deleted_image.pk).exists()
