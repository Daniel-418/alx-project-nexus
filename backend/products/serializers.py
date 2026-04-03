from rest_framework import serializers
from products.models import Product, ProductImage, Variant, OptionType, OptionValue
from categories.models import Category
from categories.serializers import CategoryOutputSerializer


class OptionValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionValue
        fields = ["id", "value", "option_type"]


class OptionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionType
        fields = ["id", "option_type"]


class OptionValueInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionValue
        fields = ["value", "option_type"]


class VariantOutputSerializer(serializers.ModelSerializer):
    option_values = OptionValueSerializer(many=True, read_only=True)
    # expose linked image IDs in output
    images = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Variant
        fields = [
            "id",
            "option_values",
            "images",
            "sku",
            "stock",
            "is_master",
            "price",
            "created_at",
            "deleted_at",
        ]
        read_only_fields = fields


class VariantInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = [
            "price",
            "option_values",
            "stock",
            "images",
            "sku",
            "is_master",
        ]
        read_only_fields = ["created_at"]

    # reject images that don't belong to the variant's product
    def validate_images(self, images):
        product_id = self.context.get("product_id")
        if product_id is None and self.instance:
            product_id = str(self.instance.product_id)

        for image in images:
            if str(image.product_id) != str(product_id):
                raise serializers.ValidationError(
                    f"Image '{image.id}' does not belong to this product."
                )
        return images

    # enforce only one master variant per product
    def validate(self, attrs):
        is_master = attrs.get("is_master", False)
        if is_master:
            product_id = self.context.get("product_id")
            if product_id is None and self.instance:
                product_id = str(self.instance.product_id)

            qs = Variant.objects.filter(product_id=product_id, is_master=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"is_master": "A master variant already exists for this product."}
                )
        return attrs


# serializer for the dedicated variant images add/remove action
class VariantImagesSerializer(serializers.Serializer):
    images = serializers.PrimaryKeyRelatedField(
        queryset=ProductImage.objects.all(), many=True
    )

    # reject images that don't belong to the variant's product
    def validate_images(self, images):
        product_id = self.context.get("product_id")
        for image in images:
            if str(image.product_id) != str(product_id):
                raise serializers.ValidationError(
                    f"Image '{image.id}' does not belong to this product."
                )
        return images


class ProductImageInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            "image",
            "alt_text",
            "is_feature",
            "display_order",
        ]

    # reject duplicate display orders before hitting the db constraint
    def validate_display_order(self, display_order):
        if display_order is None:
            return display_order

        product_id = self.context.get("product_id")
        qs = ProductImage.objects.filter(
            product_id=product_id, display_order=display_order
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"Display order {display_order} is already taken for this product."
            )
        return display_order


class ProductImageOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"


class ProductInputSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), required=False
    )

    class Meta:
        model = Product
        fields = ["name", "price", "description", "created_at", "categories"]
        read_only_fields = ["created_at"]


class ProductOutputSerializer(serializers.ModelSerializer):
    variants = VariantOutputSerializer(many=True, read_only=True)
    images = ProductImageOutputSerializer(
        source="product_images", many=True, read_only=True
    )
    categories = CategoryOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "description",
            "created_at",
            "variants",
            "images",
            "categories",
            "deleted_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "deleted_at",
            "name",
            "price",
            "variants",
        ]
