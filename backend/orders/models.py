# type: ignore
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from accounts.models import User


class OrderAddress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    phone = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.address_line_1} {self.city} {self.state}, {self.country}"


class Order(models.Model):
    class OrderStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    class FulfillmentType(models.TextChoices):
        DELIVERY = "delivery", "Delivery"
        PICKUP = "pickup", "Pickup"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    contact_email = models.EmailField()
    fulfillment_type = models.CharField(
        max_length=20,
        choices=FulfillmentType.choices,
        default=FulfillmentType.DELIVERY,
    )
    # Null for pickup orders — shipping is handled at the store.
    shipping_address = models.ForeignKey(
        OrderAddress,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="shipping_orders",
    )
    # Null when not applicable (e.g. cash with no formal billing).
    billing_address = models.ForeignKey(
        OrderAddress,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="billing_orders",
    )
    notes = models.TextField(blank=True, default="")
    guest_token = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=25, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if (
            self.fulfillment_type == self.FulfillmentType.DELIVERY
            and not self.shipping_address_id
        ):
            raise ValidationError(
                {"shipping_address": "Delivery orders require a shipping address."}
            )
        if (
            self.fulfillment_type == self.FulfillmentType.PICKUP
            and self.shipping_address_id
        ):
            raise ValidationError(
                {"shipping_address": "Pickup orders must not have a shipping address."}
            )

    @property
    def total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.price_at_purchase * order_item.quantity
        return total

    # snapshots cart items into order lines, assigns guest_token for guest carts, and saves the order
    @classmethod
    def create_from_cart(
        cls,
        cart,
        fulfillment_type,
        shipping_address=None,
        billing_address=None,
        guest_email=None,
        notes="",
    ):
        contact_email = cart.user.email if cart.user else guest_email
        guest_token = cart.session_id if cart.user is None else None

        order = cls(
            user=cart.user,
            contact_email=contact_email,
            fulfillment_type=fulfillment_type,
            shipping_address=shipping_address,
            billing_address=billing_address,
            notes=notes,
            guest_token=guest_token,
        )
        order.full_clean()
        order.save()
        for cart_item in cart.items.select_related("variant__product").prefetch_related(
            "variant__option_values__option_type"
        ):
            OrderItem.create_from_variant(order, cart_item.variant, cart_item.quantity)
        return order


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "products.Variant",
        null=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    sku_at_purchase = models.CharField(max_length=225)
    price_at_purchase = models.DecimalField(decimal_places=2, max_digits=15)
    product_name_at_purchase = models.CharField(max_length=50)
    options_at_purchase = models.JSONField(default=dict)

    @classmethod
    def create_from_variant(cls, order, variant, quantity):
        options = {
            option_value.option_type.option_type: option_value.value
            for option_value in variant.option_values.all()
        }
        return cls.objects.create(
            order=order,
            variant=variant,
            quantity=quantity,
            sku_at_purchase=variant.sku,
            price_at_purchase=variant.price,
            product_name_at_purchase=variant.product.name,
            options_at_purchase=options,
        )
