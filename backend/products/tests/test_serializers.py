# type: ignore
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
import pytest
from products.models import Product, ProductImage
from products.tests.factories import (
    OptionValueFactory,
    ProductFactory,
    ProductImageFactory,
    VariantFactory,
)
from products.serializers import (
    OptionValueSerializer,
    ProductImageInputSerializer,
    ProductInputSerializer,
    ProductOutputSerializer,
    VariantInputSerializer,
    VariantOutputSerializer,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    product = ProductFactory(name="t-shirt")
    yield product


@pytest.fixture
def variant(product):
    option_values = [OptionValueFactory(), OptionValueFactory()]
    variant = VariantFactory(product=product, option_values=option_values)
    yield variant


@pytest.fixture
def option_value():
    option_value = OptionValueFactory()
    yield option_value


@pytest.fixture
def image():
    image = SimpleUploadedFile(
        name="test_image.jpg",
        content_type="image/jpeg",
        content=b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9"
        b"\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00"
        b"\x00\x02\x02\x4c\x01\x00\x3b",
    )
    yield image


@pytest.mark.it("test product output data")
class TestProductOutputSerializer:
    @pytest.mark.it(
        "test that the product output returns correct data without a variant"
    )
    def test_serializer_returns_correct_data(self, product):

        serializer = ProductOutputSerializer(instance=product)
        expected_data = {
            "id": str(product.id),
            "name": product.name,
            "description": product.description,
            "price": str(product.price),
            "created_at": serializer.fields["created_at"].to_representation(
                product.created_at
            ),
            "deleted_at": serializer.fields["deleted_at"].to_representation(
                product.deleted_at
            ),
            "variants": [],
        }

        assert serializer.data == expected_data

    @pytest.mark.it("test that a product that has a variant returns correct data")
    def test_serializer_reutrns_correct_data_with_variant(self, product, variant):
        serializer = ProductOutputSerializer(instance=product)
        variant_serializer = VariantOutputSerializer(instance=variant)
        expected_data = {
            "id": str(product.id),
            "name": product.name,
            "description": product.description,
            "price": str(product.price),
            "created_at": serializer.fields["created_at"].to_representation(
                product.created_at
            ),
            "deleted_at": serializer.fields["deleted_at"].to_representation(
                product.deleted_at
            ),
            "variants": [variant_serializer.data],
        }

        assert serializer.data == expected_data

    @pytest.mark.it("test that deleted variants don't show in the output")
    def test_deleted_variant_is_excluded_from_output(self, product, variant):
        deleted_variant = VariantFactory(product=product)
        deleted_variant.delete()

        serializer = ProductOutputSerializer(instance=product)

        assert len(serializer.data["variants"]) == 1
        assert serializer.data["variants"][0]["id"] == str(variant.id)

    @pytest.mark.it(
        "test that a product with multiple variants return all of the variants"
    )
    def test_serializer_returns_mulitple_variants(self, product):
        variant_1 = VariantFactory(product=product)
        variant_2 = VariantFactory(product=product)

        serializer = ProductOutputSerializer(instance=product)

        assert len(serializer.data["variants"]) == 2

        serialized_ids = [v["id"] for v in serializer.data["variants"]]
        assert str(variant_1.id) in serialized_ids
        assert str(variant_2.id) in serialized_ids


@pytest.mark.describe("test the product input serializer")
class TestProductInputSerializer:
    @pytest.mark.it("ensures that the serializer correctly creates a product")
    def test_serializer_creates_product(self):
        data = {
            "name": "t-shirt",
            "price": "50.00",
            "description": "a very good shirt to wear",
        }
        serializer = ProductInputSerializer(data=data)
        assert serializer.is_valid()

        product = serializer.save()
        assert product.name == data["name"]
        assert str(product.price) == data["price"]
        assert Product.objects.get(id=product.id) == product


@pytest.mark.describe("test the VariantOutputSerializer")
class TestVariantOutputSerializer:
    @pytest.mark.it("ensures that the serializer displays a variant")
    def test_serializer_displays_variant(self, variant):
        serializer = VariantOutputSerializer(instance=variant)
        option_values_data = OptionValueSerializer(
            instance=variant.option_values.all(), many=True
        ).data
        expected_data = {
            "id": str(variant.id),
            "option_values": option_values_data,
            "sku": variant.sku,
            "stock": variant.stock,
            "is_master": variant.is_master,
            "price": str(variant.price),
            "created_at": serializer.fields["created_at"].to_representation(
                variant.created_at
            ),
            "deleted_at": serializer.fields["deleted_at"].to_representation(
                variant.deleted_at
            ),
        }
        assert serializer.data == expected_data


@pytest.mark.describe("test the variant input serializer")
class TestVariantInputSerializer:
    @pytest.mark.it("test the happy path that creates a variant")
    def test_variant_create_serializer(self, product):
        data = {
            "product": str(product.id),
            "price": "50.00",
            "option_values": [],
            "stock": 1,
            "sku": "LAP-400-1234",
            "is_master": False,
        }

        serializer = VariantInputSerializer(data=data)
        assert serializer.is_valid()

        variant = serializer.save()
        assert variant.product == product
        assert variant.price == 50
        assert variant.sku == data["sku"]

    @pytest.mark.it("test creates a variant with an option value")
    def test_create_a_variant_with_an_option_value(self, product, option_value):
        data = {
            "product": str(product.id),
            "price": "50.00",
            "option_values": [str(option_value.id)],
            "stock": 1,
            "sku": "LAP-400-1234",
            "is_master": False,
        }

        serializer = VariantInputSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        variant = serializer.save()

        assert variant.option_values.count() == 1
        assert option_value in variant.option_values.all()

    @pytest.mark.it("test validation fails if SKU is not unique")
    def test_variant_create_duplicate_sku(self, product, variant):
        data = {
            "product": str(product.id),
            "price": "50.00",
            "option_values": [],
            "stock": 1,
            "sku": variant.sku,
            "is_master": False,
        }

        serializer = VariantInputSerializer(data=data)

        assert not serializer.is_valid()

        assert "sku" in serializer.errors
        assert serializer.errors["sku"][0].code == "unique"


class TestProductImageInputSerializer:
    @pytest.mark.it("test that you can create a new product image")
    def test_product_image_creation(self, product, image):
        data = {
            "product": str(product.id),
            "image": image,
            "alt_text": "this is an example alt text",
            "is_feature": False,
            "display_order": 1,
        }

        serializer = ProductImageInputSerializer(data=data)

        assert serializer.is_valid()

        new_image = serializer.save()
        assert new_image.product == product
        assert new_image.image
        assert "test_image" in new_image.image.name
        assert new_image.alt_text == data["alt_text"]

    def test_duplicate_display_order(self, product, image):
        image1 = ProductImageFactory(product=product)
        data = {
            "product": str(product.id),
            "image": image,
            "alt_text": "this is an example alt text",
            "is_feature": False,
            "display_order": 1,
        }

        serializer = ProductImageInputSerializer(data=data)

        assert serializer.is_valid()

        with pytest.raises(IntegrityError):
            serializer.save()
