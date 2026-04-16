# type: ignore
import pytest
from django.urls import reverse

from cart.models import Cart
from cart.tests.factories import CartFactory, CartItemFactory
from core.tests.fixtures import (
    anonymous_user,
    pytestmark,
    staff_client,
    standard_user_client,
)
from orders.models import Order
from orders.tests.factories import OrderAddressFactory, OrderFactory, OrderItemFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def order_list_url():
    return reverse("order-list")


@pytest.fixture
def address_data():
    addr = OrderAddressFactory.build()
    return {
        "first_name": addr.first_name,
        "last_name": addr.last_name,
        "address_line_1": addr.address_line_1,
        "address_line_2": addr.address_line_2,
        "city": addr.city,
        "state": addr.state,
        "postal_code": addr.postal_code,
        "country": addr.country,
        "phone": addr.phone,
    }


@pytest.mark.describe("OrderViewset — create")
class TestOrderCreate:
    @pytest.mark.it(
        "guest checkout with contact_email and shipping address returns 201"
    )
    def test_guest_checkout_returns_201(
        self, anonymous_user, order_list_url, address_data
    ):
        cart = CartFactory()
        CartItemFactory(cart=cart)

        payload = {
            "cart": str(cart.id),
            "contact_email": "guest@example.com",
            "fulfillment_type": "delivery",
            "shipping_address": address_data,
        }
        response = anonymous_user.post(order_list_url, data=payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert len(data["items"]) == 1
        assert data["contact_email"] == "guest@example.com"

    @pytest.mark.it("authenticated checkout links order to the requesting user")
    def test_authenticated_checkout_links_order_to_user(
        self, standard_user_client, order_list_url, address_data
    ):
        cart = CartFactory(user=standard_user_client.user)
        CartItemFactory(cart=cart)

        payload = {
            "cart": str(cart.id),
            "fulfillment_type": "delivery",
            "shipping_address": address_data,
        }
        response = standard_user_client.post(
            order_list_url, data=payload, format="json"
        )

        assert response.status_code == 201
        data = response.json()
        assert str(data["user"]) == str(standard_user_client.user.id)

    @pytest.mark.it("cart is deleted after a successful order creation")
    def test_cart_is_deleted_after_order_creation(
        self, anonymous_user, order_list_url, address_data
    ):
        cart = CartFactory()
        CartItemFactory(cart=cart)

        payload = {
            "cart": str(cart.id),
            "contact_email": "guest@example.com",
            "fulfillment_type": "delivery",
            "shipping_address": address_data,
        }
        anonymous_user.post(order_list_url, data=payload, format="json")

        assert not Cart.objects.filter(pk=cart.pk).exists()

    @pytest.mark.it("empty cart returns 400 with error on cart key")
    def test_empty_cart_returns_400(self, anonymous_user, order_list_url, address_data):
        cart = CartFactory()  # no items

        payload = {
            "cart": str(cart.id),
            "contact_email": "guest@example.com",
            "fulfillment_type": "delivery",
            "shipping_address": address_data,
        }
        response = anonymous_user.post(order_list_url, data=payload, format="json")

        assert response.status_code == 400
        assert "cart" in response.json()

    @pytest.mark.it("guest cart without contact_email returns 400")
    def test_guest_cart_without_contact_email_returns_400(
        self, anonymous_user, order_list_url, address_data
    ):
        cart = CartFactory()  # no user — guest cart
        CartItemFactory(cart=cart)

        payload = {
            "cart": str(cart.id),
            "fulfillment_type": "delivery",
            "shipping_address": address_data,
        }
        response = anonymous_user.post(order_list_url, data=payload, format="json")

        assert response.status_code == 400
        assert "contact_email" in response.json()


@pytest.mark.describe("OrderViewset — cancel")
class TestOrderCancel:
    pytest.mark.it("test guest can cancel an order")

    def test_an_order_can_be_cancelled_by_an_unauthenticated_user(
        self, address_data, anonymous_user, order_list_url
    ):
        cart = CartFactory()
        CartItemFactory(cart=cart)

        payload = {
            "cart": str(cart.id),
            "contact_email": "guest@example.com",
            "fulfillment_type": "delivery",
            "shipping_address": address_data,
        }
        create_response = anonymous_user.post(
            order_list_url, data=payload, format="json"
        )
        assert create_response.status_code == 201
        data = create_response.json()

        response = anonymous_user.post(
            reverse("order-cancel", kwargs={"pk": data["id"]}),
            data={"guest_token": data["guest_token"]},
            format="json",
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == Order.OrderStatus.CANCELLED

    @pytest.mark.it("authenticated user can cancel their own pending order")
    def test_authenticated_user_can_cancel_own_order(self, standard_user_client):
        order = OrderFactory(user=standard_user_client.user)
        OrderItemFactory(order=order)

        response = standard_user_client.post(
            reverse("order-cancel", kwargs={"pk": order.id}), format="json"
        )

        assert response.status_code == 200, response.text
        order.refresh_from_db()
        assert order.status == Order.OrderStatus.CANCELLED

    @pytest.mark.it("staff can cancel any order")
    def test_staff_can_cancel_any_order(self, staff_client):
        order = OrderFactory()
        OrderItemFactory(order=order)

        response = staff_client.post(
            reverse("order-cancel", kwargs={"pk": order.id}), format="json"
        )

        assert response.status_code == 200, response.text
        order.refresh_from_db()
        assert order.status == Order.OrderStatus.CANCELLED

    @pytest.mark.it("non-staff cannot cancel an order outside the cancellable window")
    def test_non_staff_cannot_cancel_in_flight_order(self, standard_user_client):
        order = OrderFactory(
            user=standard_user_client.user, status=Order.OrderStatus.PROCESSING
        )
        OrderItemFactory(order=order)

        response = standard_user_client.post(
            reverse("order-cancel", kwargs={"pk": order.id}), format="json"
        )

        assert response.status_code == 400
        order.refresh_from_db()
        assert order.status == Order.OrderStatus.PROCESSING

    @pytest.mark.it("staff can cancel an order outside the cancellable window")
    def test_staff_can_cancel_in_flight_order(self, staff_client):
        order = OrderFactory(status=Order.OrderStatus.PROCESSING)
        OrderItemFactory(order=order)

        response = staff_client.post(
            reverse("order-cancel", kwargs={"pk": order.id}), format="json"
        )

        assert response.status_code == 200, response.text
        order.refresh_from_db()
        assert order.status == Order.OrderStatus.CANCELLED


@pytest.mark.describe("OrderViewset — list")
class TestOrderList:
    @pytest.mark.it("authenticated user sees only their own orders")
    def test_authenticated_user_sees_own_orders(
        self, standard_user_client, order_list_url
    ):
        own = OrderFactory(user=standard_user_client.user)
        OrderFactory()  # another user's order
        response = standard_user_client.get(order_list_url)
        assert response.status_code == 200
        ids = [o["id"] for o in response.json()]
        assert str(own.id) in ids
        assert len(ids) == 1

    @pytest.mark.it("staff sees all orders")
    def test_staff_sees_all_orders(self, staff_client, order_list_url):
        OrderFactory()
        OrderFactory()
        response = staff_client.get(order_list_url)
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.it("unauthenticated user is rejected")
    def test_unauthenticated_gets_401(self, anonymous_user, order_list_url):
        response = anonymous_user.get(order_list_url)
        assert response.status_code == 401


@pytest.mark.describe("OrderViewset — retrieve")
class TestOrderRetrieve:
    @pytest.mark.it("owner can retrieve their own order")
    def test_owner_can_retrieve_own_order(self, standard_user_client):
        order = OrderFactory(user=standard_user_client.user)
        response = standard_user_client.get(
            reverse("order-detail", kwargs={"pk": order.id})
        )
        assert response.status_code == 200
        assert str(response.json()["id"]) == str(order.id)

    @pytest.mark.it("authenticated user cannot retrieve another user's order")
    def test_cannot_retrieve_other_users_order(self, standard_user_client):
        other_order = OrderFactory()  # belongs to no user — not in requester's queryset
        response = standard_user_client.get(
            reverse("order-detail", kwargs={"pk": other_order.id})
        )
        assert response.status_code == 404

    @pytest.mark.it("staff can retrieve any order")
    def test_staff_can_retrieve_any_order(self, staff_client):
        order = OrderFactory()
        response = staff_client.get(reverse("order-detail", kwargs={"pk": order.id}))
        assert response.status_code == 200
        assert str(response.json()["id"]) == str(order.id)


@pytest.mark.describe("OrderViewset - update status")
class TestOrderUpdate:
    @pytest.mark.it("staff can update order status")
    def test_staff_can_update_order_status(self, staff_client):
        order = OrderFactory(status=Order.OrderStatus.PENDING)
        response = staff_client.patch(
            reverse("order-update-status", kwargs={"pk": order.id}),
            data={"status": Order.OrderStatus.CONFIRMED},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == Order.OrderStatus.CONFIRMED

    @pytest.mark.it("non-staff cannot update order status")
    def test_non_staff_cannot_update_order_status(self, standard_user_client):
        order = OrderFactory(user=standard_user_client.user)
        response = standard_user_client.patch(
            reverse("order-update-status", kwargs={"pk": order.id}),
            data={"status": Order.OrderStatus.CONFIRMED},
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.it("invalid status returns 400")
    def test_invalid_status_returns_400(self, staff_client):
        order = OrderFactory()
        response = staff_client.patch(
            reverse("order-update-status", kwargs={"pk": order.id}),
            data={"status": "invalid"},
            format="json",
        )
        assert response.status_code == 400
        assert "status" in response.json()
