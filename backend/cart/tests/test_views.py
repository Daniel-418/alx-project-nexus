# type: ignore

from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from products.tests.factories import VariantFactory
import uuid
from django.urls import reverse
import pytest
from cart.tests.factories import CartFactory, CartItemFactory
from core.tests.fixtures import (
    anonymous_user,
    standard_user_client,
    pytestmark,
)


@pytest.fixture
def create_cart_url():
    return reverse("cart-list")


@pytest.mark.describe("test that a cart can be created")
class TestCartCreation:
    @pytest.mark.it(
        "guest can create a cart without a session header and receives a session_id"
    )
    def test_that_a_cart_can_be_created(self, create_cart_url, anonymous_user):
        response = anonymous_user.post(create_cart_url)
        assert response.status_code == 201

        data = response.json()
        assert "session_id" in data
        assert "id" in data
        assert "items" in data


@pytest.mark.describe("CartViewset — queryset scoping")
class TestCartQuerysetScoping:
    @pytest.mark.it("authenticated user only sees their own carts")
    def test_authenticated_user_sees_own_cart_only(self, standard_user_client):
        own_cart = CartFactory(user=standard_user_client.user)
        CartFactory()  # another user's cart

        response = standard_user_client.get(reverse("cart-list"))
        assert response.status_code == 200
        ids = [c["id"] for c in response.json()["results"]]
        assert str(own_cart.id) in ids
        assert len(ids) == 1

    @pytest.mark.it("guest user only sees their own session cart")
    def test_guest_user_sees_own_session_cart_only(self, anonymous_user):
        session_id = uuid.uuid4()
        own_cart = CartFactory(session_id=session_id)
        CartFactory()  # different session

        anonymous_user.credentials(HTTP_X_CART_SESSION=str(session_id))
        response = anonymous_user.get(reverse("cart-list"))
        assert response.status_code == 200
        ids = [c["id"] for c in response.json()["results"]]
        assert str(own_cart.id) in ids
        assert len(ids) == 1


@pytest.mark.describe("CartViewset — perform_create")
class TestCartPerformCreate:
    @pytest.mark.it("cart created by authenticated user is linked to that user")
    def test_cart_links_to_authenticated_user_on_create(self, standard_user_client):
        response = standard_user_client.post(reverse("cart-list"))
        assert response.status_code == 201
        data = response.json()
        assert str(data["user"]) == str(standard_user_client.user.id)


@pytest.mark.describe("IsCartOwner — has_permission")
class TestIsCartOwnerHasPermission:
    @pytest.mark.it(
        "unauthenticated request without session header is blocked from non-create actions"
    )
    def test_guest_without_session_header_is_blocked(self, anonymous_user):
        cart = CartFactory()
        response = anonymous_user.get(reverse("cart-detail", args=[cart.id]))
        assert response.status_code == 401


@pytest.mark.describe("CartItemViewset — nested under cart")
class TestCartItemViewset:
    @pytest.fixture
    def user_cart(self, standard_user_client):
        return CartFactory(user=standard_user_client.user)

    def item_list_url(self, cart_id):
        return reverse("cart-items-list", args=[cart_id])

    @pytest.mark.it("only items belonging to the cart are returned")
    def test_only_cart_items_returned(self, standard_user_client, user_cart):
        item = CartItemFactory(cart=user_cart)
        CartItemFactory()  # item on a different cart

        response = standard_user_client.get(self.item_list_url(user_cart.id))
        assert response.status_code == 200
        ids = [i["id"] for i in response.json()["results"]]
        assert str(item.id) in ids
        assert len(ids) == 1

    @pytest.mark.it("listing items from another user's cart returns 404")
    def test_cannot_list_other_users_cart_items(self, standard_user_client):
        other_cart = CartFactory()
        CartItemFactory(cart=other_cart)

        response = standard_user_client.get(self.item_list_url(other_cart.id))
        assert response.status_code == 404

    @pytest.mark.it("creating a cart item links it to the parent cart")
    def test_create_item_links_to_cart(self, standard_user_client, user_cart):

        variant = VariantFactory(stock=10)
        response = standard_user_client.post(
            self.item_list_url(user_cart.id),
            {"variant": str(variant.id), "quantity": 2},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["quantity"] == 2

    @pytest.mark.it("cannot add item to another user's cart")
    def test_cannot_add_item_to_other_users_cart(self, standard_user_client):
        other_cart = CartFactory()

        variant = VariantFactory()
        response = standard_user_client.post(
            self.item_list_url(other_cart.id),
            {"variant": str(variant.id), "quantity": 1},
        )
        assert response.status_code in (403, 404)

    @pytest.mark.it("quantity=0 is rejected")
    def test_quantity_zero_rejected(self, standard_user_client, user_cart):

        variant = VariantFactory()
        response = standard_user_client.post(
            self.item_list_url(user_cart.id),
            {"variant": str(variant.id), "quantity": 0},
        )
        assert response.status_code == 400

    @pytest.mark.it("quantity exceeding stock is rejected")
    def test_quantity_exceeding_stock_rejected(self, standard_user_client, user_cart):

        variant = VariantFactory(stock=3)
        response = standard_user_client.post(
            self.item_list_url(user_cart.id),
            {"variant": str(variant.id), "quantity": 5},
        )
        assert response.status_code == 400

    @pytest.mark.it(
        "adding the same variant twice increments quantity instead of erroring"
    )
    def test_duplicate_variant_increments_quantity(
        self, standard_user_client, user_cart
    ):

        variant = VariantFactory(stock=10)
        standard_user_client.post(
            self.item_list_url(user_cart.id),
            {"variant": str(variant.id), "quantity": 3},
        )
        response = standard_user_client.post(
            self.item_list_url(user_cart.id),
            {"variant": str(variant.id), "quantity": 2},
        )
        assert response.status_code == 200
        assert response.json()["quantity"] == 5

    @pytest.mark.it("incrementing beyond stock is rejected")
    def test_increment_beyond_stock_rejected(self, standard_user_client, user_cart):

        variant = VariantFactory(stock=4)
        CartItemFactory(cart=user_cart, variant=variant, quantity=3)
        response = standard_user_client.post(
            self.item_list_url(user_cart.id),
            {"variant": str(variant.id), "quantity": 2},
        )
        assert response.status_code == 400


@pytest.mark.describe("CartViewset — clear action")
class TestCartClear:
    @pytest.fixture
    def user_cart(self, standard_user_client):
        return CartFactory(user=standard_user_client.user)

    def clear_url(self, cart_id):
        return reverse("cart-clear", args=[cart_id])

    @pytest.mark.it("clear removes all items and returns an empty cart")
    def test_clear_empties_cart(self, standard_user_client, user_cart):
        CartItemFactory(cart=user_cart)
        CartItemFactory(cart=user_cart)

        response = standard_user_client.post(self.clear_url(user_cart.id))
        assert response.status_code == 200
        assert response.json()["items"] == []

    @pytest.mark.it("clear on another user's cart returns 404")
    def test_clear_other_users_cart_blocked(self, standard_user_client):
        other_cart = CartFactory()
        response = standard_user_client.post(self.clear_url(other_cart.id))
        assert response.status_code == 404


@pytest.mark.describe("CartViewset — guest cart expiry")
class TestGuestCartExpiry:
    @pytest.mark.it("guest cart creation sets expires_at approximately 30 days from now")
    def test_guest_cart_has_expires_at(self, anonymous_user):
        response = anonymous_user.post(reverse("cart-list"))
        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is not None
        expires = parse_datetime(data["expires_at"])
        expected = timezone.now() + timedelta(days=30)
        assert abs((expires - expected).total_seconds()) < 5

    @pytest.mark.it("authenticated cart creation leaves expires_at as null")
    def test_authenticated_cart_has_no_expires_at(self, standard_user_client):
        response = standard_user_client.post(reverse("cart-list"))
        assert response.status_code == 201
        assert response.json()["expires_at"] is None


@pytest.mark.describe("clean_expired_carts management command")
class TestCleanExpiredCartsCommand:
    @pytest.mark.it("only deletes expired guest carts; leaves live guest and auth carts intact")
    def test_only_expired_guest_carts_deleted(self):
        from django.core.management import call_command
        from accounts.tests.factories import UserFactory

        expired = CartFactory(user=None, expires_at=timezone.now() - timedelta(days=1))
        live_guest = CartFactory(user=None, expires_at=timezone.now() + timedelta(days=29))
        auth_cart = CartFactory(user=UserFactory(), expires_at=None)

        call_command("clean_expired_carts", verbosity=0)

        from cart.models import Cart as CartModel

        remaining = list(CartModel.objects.values_list("id", flat=True))
        assert expired.id not in remaining
        assert live_guest.id in remaining
        assert auth_cart.id in remaining


@pytest.mark.describe("CartViewset — merge action")
class TestCartMerge:
    @pytest.fixture
    def user_cart(self, standard_user_client):
        return CartFactory(user=standard_user_client.user)

    @pytest.fixture
    def guest_cart(self):
        return CartFactory(user=None, expires_at=timezone.now() + timedelta(days=30))

    def merge_url(self, cart_id):
        return reverse("cart-merge", args=[cart_id])

    @pytest.mark.it("authenticated user can merge a guest cart into their cart")
    def test_authenticated_user_can_merge(self, standard_user_client, user_cart, guest_cart):
        variant = VariantFactory(stock=10)
        CartItemFactory(cart=guest_cart, variant=variant, quantity=2)

        response = standard_user_client.post(
            self.merge_url(user_cart.id), {"session_id": str(guest_cart.session_id)}
        )
        assert response.status_code == 200
        variant_ids = [i["variant"]["id"] for i in response.json()["items"]]
        assert str(variant.id) in variant_ids

    @pytest.mark.it("duplicate variants have quantities summed during merge")
    def test_merge_adds_quantities(self, standard_user_client, user_cart, guest_cart):
        variant = VariantFactory(stock=20)
        CartItemFactory(cart=user_cart, variant=variant, quantity=3)
        CartItemFactory(cart=guest_cart, variant=variant, quantity=4)

        response = standard_user_client.post(
            self.merge_url(user_cart.id), {"session_id": str(guest_cart.session_id)}
        )
        assert response.status_code == 200
        matching = [i for i in response.json()["items"] if i["variant"]["id"] == str(variant.id)]
        assert len(matching) == 1
        assert matching[0]["quantity"] == 7

    @pytest.mark.it("quantities are clamped to stock on overflow during merge")
    def test_merge_clamps_to_stock(self, standard_user_client, user_cart, guest_cart):
        variant = VariantFactory(stock=5)
        CartItemFactory(cart=user_cart, variant=variant, quantity=4)
        CartItemFactory(cart=guest_cart, variant=variant, quantity=4)

        response = standard_user_client.post(
            self.merge_url(user_cart.id), {"session_id": str(guest_cart.session_id)}
        )
        assert response.status_code == 200
        matching = [i for i in response.json()["items"] if i["variant"]["id"] == str(variant.id)]
        assert matching[0]["quantity"] == 5

    @pytest.mark.it("guest cart is deleted after a successful merge")
    def test_guest_cart_deleted_after_merge(self, standard_user_client, user_cart, guest_cart):
        CartItemFactory(cart=guest_cart)

        standard_user_client.post(
            self.merge_url(user_cart.id), {"session_id": str(guest_cart.session_id)}
        )

        from cart.models import Cart as CartModel

        assert not CartModel.objects.filter(id=guest_cart.id).exists()

    @pytest.mark.it("unauthenticated user cannot call merge")
    def test_unauthenticated_cannot_merge(self, anonymous_user, user_cart):
        response = anonymous_user.post(
            self.merge_url(user_cart.id), {"session_id": str(uuid.uuid4())}
        )
        assert response.status_code == 401

    @pytest.mark.it("unknown session_id returns 404")
    def test_unknown_session_id_returns_404(self, standard_user_client, user_cart):
        response = standard_user_client.post(
            self.merge_url(user_cart.id), {"session_id": str(uuid.uuid4())}
        )
        assert response.status_code == 404
