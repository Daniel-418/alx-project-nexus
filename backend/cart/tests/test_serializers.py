# type: ignore
import pytest
from cart.tests.factories import CartFactory, CartItemFactory
from cart.serializers import CartOutputSerializer

pytestmark = pytest.mark.django_db


class TestCartOutputSerializer:
    @pytest.mark.it("test that cart output nests items inline")
    def test_items_are_nested_inline(self):
        cart = CartFactory()
        item_1 = CartItemFactory(cart=cart)
        item_2 = CartItemFactory(cart=cart)

        serializer = CartOutputSerializer(instance=cart)
        item_ids = [i["id"] for i in serializer.data["items"]]

        assert len(serializer.data["items"]) == 2
        assert str(item_1.id) in item_ids
        assert str(item_2.id) in item_ids

    @pytest.mark.it("each nested item exposes nested variant detail, not just an id")
    def test_nested_item_has_variant_detail(self):
        cart = CartFactory()
        item = CartItemFactory(cart=cart)

        serializer = CartOutputSerializer(instance=cart)
        item_data = serializer.data["items"][0]

        assert isinstance(item_data["variant"], dict)
        assert str(item.variant.id) == item_data["variant"]["id"]

    @pytest.mark.it("total is zero for a cart with no items")
    def test_total_is_zero_for_empty_cart(self):
        cart = CartFactory()
        data = CartOutputSerializer(instance=cart).data
        assert data["total"] == 0

    @pytest.mark.it("total equals sum of variant price times quantity across all items")
    def test_total_reflects_items(self):
        cart = CartFactory()
        item_1 = CartItemFactory(cart=cart, quantity=2)
        item_2 = CartItemFactory(cart=cart, quantity=3)

        expected = (item_1.variant.price * 2) + (item_2.variant.price * 3)
        data = CartOutputSerializer(instance=cart).data
        assert data["total"] == expected
