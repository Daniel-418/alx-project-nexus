from rest_framework.relations import PrimaryKeyRelatedField
from cart.models import Cart
from orders.models import OrderAddress, Order, OrderItem
from rest_framework import serializers


class OrderAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAddress
        fields = [
            "first_name",
            "last_name",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "phone",
        ]


class OrderItemOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "variant",
            "quantity",
            "sku_at_purchase",
            "price_at_purchase",
            "product_name_at_purchase",
            "options_at_purchase",
        ]
        read_only_fields = fields


class OrderInputSerializer(serializers.ModelSerializer):
    cart = PrimaryKeyRelatedField(queryset=Cart.objects.all())
    # required only for guest carts — auth cart users get it from cart.user.email
    contact_email = serializers.EmailField(required=False)
    shipping_address = OrderAddressSerializer(required=False, allow_null=True)
    billing_address = OrderAddressSerializer(required=False, allow_null=True)

    class Meta:
        model = Order
        fields = [
            "cart",
            "contact_email",
            "fulfillment_type",
            "shipping_address",
            "billing_address",
            "notes",
        ]

    def validate(self, attrs):
        cart = attrs.get("cart")
        fulfillment_type = attrs.get("fulfillment_type", Order.FulfillmentType.DELIVERY)
        shipping_address = attrs.get("shipping_address")

        if cart and not cart.items.exists():
            raise serializers.ValidationError(
                {"cart": "Cannot create an order from an empty cart."}
            )
        if cart and cart.user is None and not attrs.get("contact_email"):
            raise serializers.ValidationError(
                {"contact_email": "Guest carts require a contact email."}
            )
        if fulfillment_type == Order.FulfillmentType.DELIVERY and not shipping_address:
            raise serializers.ValidationError(
                {"shipping_address": "Delivery orders require a shipping address."}
            )
        if fulfillment_type == Order.FulfillmentType.PICKUP and shipping_address:
            raise serializers.ValidationError(
                {"shipping_address": "Pickup orders must not have a shipping address."}
            )
        return attrs

    def create(self, validated_data):
        cart = validated_data.pop("cart")
        contact_email = validated_data.pop("contact_email", None)
        fulfillment_type = validated_data.pop(
            "fulfillment_type", Order.FulfillmentType.DELIVERY
        )
        notes = validated_data.pop("notes", "")

        shipping_data = validated_data.pop("shipping_address", None)
        billing_data = validated_data.pop("billing_address", None)

        shipping_address = (
            OrderAddress.objects.create(**shipping_data) if shipping_data else None
        )
        billing_address = (
            OrderAddress.objects.create(**billing_data) if billing_data else None
        )

        return Order.create_from_cart(
            cart=cart,
            fulfillment_type=fulfillment_type,
            shipping_address=shipping_address,
            billing_address=billing_address,
            guest_email=contact_email,
            notes=notes,
        )


class OrderOutputSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()
    shipping_address = OrderAddressSerializer(read_only=True)
    billing_address = OrderAddressSerializer(read_only=True)
    items = OrderItemOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "contact_email",
            "fulfillment_type",
            "shipping_address",
            "billing_address",
            "notes",
            "guest_token",
            "items",
            "total",
            "status",
            "created_at",
        ]
        read_only_fields = fields

    def get_total(self, obj):
        return obj.total
