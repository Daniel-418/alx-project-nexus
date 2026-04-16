# type: ignore
import pytest
from django.core.exceptions import ValidationError
from accounts.tests.factories import UserFactory
from cart.tests.factories import CartFactory, CartItemFactory
from orders.tests.factories import OrderAddressFactory, OrderFactory
from orders.models import Order

pytestmark = pytest.mark.django_db


@pytest.fixture
def cart():
    cart = CartFactory()
    CartItemFactory(cart=cart)
    CartItemFactory(cart=cart)
    CartItemFactory(cart=cart)
    CartItemFactory(cart=cart)
    return cart


@pytest.mark.describe("Order.create_from_cart")
class TestOrderCreation:
    @pytest.mark.it("creates a delivery order from a guest cart")
    def test_delivery_order_guest_cart(self, cart):
        shipping_address = OrderAddressFactory()

        order = Order.create_from_cart(
            cart=cart,
            fulfillment_type=Order.FulfillmentType.DELIVERY,
            shipping_address=shipping_address,
            guest_email="guest@example.com",
        )

        assert order.contact_email == "guest@example.com"
        assert order.fulfillment_type == Order.FulfillmentType.DELIVERY
        assert order.items.count() == 4
        assert order.total == cart.total
        assert order.guest_token == cart.session_id

    @pytest.mark.it("creates a delivery order and uses the cart user email")
    def test_delivery_order_authenticated_cart(self, cart):
        cart.user = UserFactory()
        shipping_address = OrderAddressFactory()

        order = Order.create_from_cart(
            cart=cart,
            fulfillment_type=Order.FulfillmentType.DELIVERY,
            shipping_address=shipping_address,
        )

        assert order.contact_email == cart.user.email
        assert order.guest_token is None

    @pytest.mark.it("creates a pickup order without a shipping address")
    def test_pickup_order(self, cart):
        order = Order.create_from_cart(
            cart=cart,
            fulfillment_type=Order.FulfillmentType.PICKUP,
            guest_email="guest@example.com",
        )

        assert order.fulfillment_type == Order.FulfillmentType.PICKUP
        assert order.shipping_address is None
        assert order.items.count() == 4


@pytest.mark.describe("Order.clean")
class TestOrderClean:
    @pytest.mark.it("raises if a delivery order has no shipping address")
    def test_delivery_requires_shipping_address(self, cart):
        with pytest.raises(ValidationError):
            Order.create_from_cart(
                cart=cart,
                fulfillment_type=Order.FulfillmentType.DELIVERY,
                guest_email="guest@example.com",
            )

    @pytest.mark.it("raises if a pickup order has a shipping address")
    def test_pickup_rejects_shipping_address(self, cart):
        shipping_address = OrderAddressFactory()

        with pytest.raises(ValidationError):
            Order.create_from_cart(
                cart=cart,
                fulfillment_type=Order.FulfillmentType.PICKUP,
                shipping_address=shipping_address,
                guest_email="guest@example.com",
            )


@pytest.mark.describe("Order.total")
class TestOrderTotal:
    @pytest.mark.it("returns zero for an order with no items")
    def test_total_is_zero_with_no_items(self):
        order = OrderFactory()

        assert order.total == 0
