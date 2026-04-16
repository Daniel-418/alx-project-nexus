from rest_framework import serializers
from cart.models import Cart, CartItem
from products.serializers import VariantOutputSerializer


class CartItemInputSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = CartItem
        fields = ["variant", "quantity"]


class CartItemOutputSerializer(serializers.ModelSerializer):
    variant = VariantOutputSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "variant", "quantity"]


class CartInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = []


class CartOutputSerializer(serializers.ModelSerializer):
    items = CartItemOutputSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total",
            "user",
            "session_id",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    # sum of variant price * quantity across all items in the cart
    def get_total(self, obj):
        return obj.total


class MergeSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
