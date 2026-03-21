from rest_framework import serializers
from products.models import Product, ProductImage, Variant, OptionType, OptionValue
from django.db import transaction


class OptionValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionValue
        fields = ["value", "option_type"]


class OptionValueInputSerializer(serializers.ModelSerializer):
    option_type = serializers.CharField()

    class Meta:
        model = OptionValue
        fields = ["value", "option_type"]


class VariantOutputSerializer(serializers.ModelSerializer):
    option_values = OptionValueSerializer(many=True, read_only=True)

    class Meta:
        model = Variant
        fields = [
            "id",
            "option_values",
            "sku",
            "stock",
            "is_master",
            "price",
            "created_at",
            "deleted_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "option_values",
            "sku",
            "stock",
            "is_master",
            "price",
            "created_at",
            "deleted_at",
        ]


class ProductInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["name", "price", "description", "created_at"]
        read_only_fields = ["created_at"]


class ProductOutputSerializer(serializers.ModelSerializer):
    variants = VariantOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "description",
            "created_at",
            "variants",
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


class VariantInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = [
            "product",
            "price",
            "option_values",
            "stock",
            "images",
            "sku",
            "is_master",
        ]
        read_only_fields = ["created_at"]


class ProductImageInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            "product",
            "image",
            "alt_text",
            "is_feature",
            "display_order",
        ]


class ProductImageOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"
        read_only_fields = "__all__"
