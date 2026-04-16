# type: ignore
import pytest
from cart.tests.factories import CartFactory, CartItemFactory
from orders.models import Order, OrderAddress
from orders.serializers import OrderInputSerializer, OrderOutputSerializer
from orders.tests.factories import OrderAddressFactory, OrderFactory, OrderItemFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def cart():
    cart = CartFactory()
    CartItemFactory(cart=cart)
    return cart


@pytest.fixture
def address_data():
    a = OrderAddressFactory.build()
    return {
        "first_name": a.first_name,
        "last_name": a.last_name,
        "address_line_1": a.address_line_1,
        "city": a.city,
        "state": a.state,
        "postal_code": a.postal_code,
        "country": a.country,
    }


@pytest.mark.describe("OrderInputSerializer.validate")
class TestOrderInputSerializerValidation:
    @pytest.mark.it(
        "rejects delivery order without shipping_address using the shipping_address error key"
    )
    def test_delivery_missing_shipping_address_raises_with_correct_key(self, cart):
        serializer = OrderInputSerializer(
            data={
                "cart": str(cart.id),
                "contact_email": "guest@example.com",
                "fulfillment_type": Order.FulfillmentType.DELIVERY,
            }
        )

        assert serializer.is_valid() is False
        assert "shipping_address" in serializer.errors
        assert (
            serializer.errors["shipping_address"][0]
            == "Delivery orders require a shipping address."
        )

    @pytest.mark.it(
        "rejects pickup order that includes a shipping_address using the shipping_address error key"
    )
    def test_pickup_with_shipping_address_raises_with_correct_key(
        self, cart, address_data
    ):
        serializer = OrderInputSerializer(
            data={
                "cart": str(cart.id),
                "contact_email": "guest@example.com",
                "fulfillment_type": Order.FulfillmentType.PICKUP,
                "shipping_address": address_data,
            }
        )
        assert serializer.is_valid() is False
        assert "shipping_address" in serializer.errors
        assert (
            serializer.errors["shipping_address"][0]
            == "Pickup orders must not have a shipping address."
        )

    @pytest.mark.it(
        "defaults missing fulfillment_type to DELIVERY and requires shipping_address"
    )
    def test_omitting_fulfillment_type_defaults_to_delivery_requires_shipping_address(
        self, cart
    ):
        serializer = OrderInputSerializer(
            data={
                "cart": str(cart.id),
                "contact_email": "guest@example.com",
            }
        )

        assert serializer.is_valid() is False
        assert "shipping_address" in serializer.errors


@pytest.mark.describe("OrderInputSerializer.create")
class TestOrderInputSerializerCreate:
    @pytest.mark.it("persists shipping_address dict as an OrderAddress DB record")
    def test_shipping_address_dict_is_persisted_as_order_address_record(
        self, cart, address_data
    ):
        serializer = OrderInputSerializer(
            data={
                "cart": str(cart.id),
                "contact_email": "guest@example.com",
                "fulfillment_type": Order.FulfillmentType.DELIVERY,
                "shipping_address": address_data,
            }
        )

        assert serializer.is_valid(), serializer.errors
        order = serializer.save()

        assert order.shipping_address is not None
        assert order.shipping_address.city == address_data["city"]
        assert OrderAddress.objects.filter(id=order.shipping_address.id).exists()

    @pytest.mark.it(
        "persists billing_address dict as an OrderAddress DB record when provided"
    )
    def test_billing_address_dict_is_persisted_when_provided(self, cart, address_data):

        billing_data = dict(address_data)
        billing_data["city"] = "Billing City"

        serializer = OrderInputSerializer(
            data={
                "cart": str(cart.id),
                "contact_email": "guest@example.com",
                "fulfillment_type": Order.FulfillmentType.DELIVERY,
                "shipping_address": address_data,
                "billing_address": billing_data,
            }
        )

        assert serializer.is_valid(), serializer.errors
        order = serializer.save()

        assert order.billing_address is not None
        assert order.billing_address.city == "Billing City"

    @pytest.mark.it(
        "leaves billing_address null and creates no extra OrderAddress when omitted"
    )
    def test_omitting_billing_address_leaves_order_billing_address_null(
        self, cart, address_data
    ):
        serializer = OrderInputSerializer(
            data={
                "cart": str(cart.id),
                "contact_email": "guest@example.com",
                "fulfillment_type": Order.FulfillmentType.DELIVERY,
                "shipping_address": address_data,
            }
        )

        assert serializer.is_valid(), serializer.errors
        order = serializer.save()

        assert order.billing_address is None
        assert OrderAddress.objects.count() == 1

    @pytest.mark.it("forwards contact_email as guest_email for a guest cart")
    def test_contact_email_is_forwarded_as_guest_email_for_guest_cart(
        self, cart, address_data
    ):
        serializer = OrderInputSerializer(
            data={
                "cart": str(cart.id),
                "contact_email": "guest@example.com",
                "fulfillment_type": Order.FulfillmentType.DELIVERY,
                "shipping_address": address_data,
            }
        )

        assert serializer.is_valid(), serializer.errors
        order = serializer.save()

        assert order.contact_email == "guest@example.com"


@pytest.mark.describe("OrderOutputSerializer")
class TestOrderOutputSerializer:
    @pytest.mark.it("total field reflects order.total property")
    def test_total_field_reflects_order_total_property(self):
        order_item = OrderItemFactory()
        order = order_item.order

        serializer = OrderOutputSerializer(order)

        assert "total" in serializer.data
        assert serializer.data["total"] == order.total
