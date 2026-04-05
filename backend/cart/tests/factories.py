# type: ignore
import factory
from cart.models import Cart, CartItem
from products.tests.factories import VariantFactory


class CartFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cart


class CartItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    variant = factory.SubFactory(VariantFactory)
    quantity = factory.Faker("pyint", min_value=1, max_value=10)
