# type: ignore
import factory
from orders.models import Order, OrderAddress, OrderItem
from products.tests.factories import VariantFactory


class OrderAddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderAddress

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    address_line_1 = factory.Faker("street_address")
    address_line_2 = factory.Faker("secondary_address")
    city = factory.Faker("city")
    state = factory.Faker("state")
    postal_code = factory.Faker("postcode")
    country = factory.Faker("country")
    phone = factory.Faker("phone_number")


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    contact_email = factory.Faker("email")
    fulfillment_type = Order.FulfillmentType.DELIVERY
    shipping_address = factory.SubFactory(OrderAddressFactory)
    billing_address = None


class PickupOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    contact_email = factory.Faker("email")
    fulfillment_type = Order.FulfillmentType.PICKUP
    shipping_address = None
    billing_address = None


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    variant = factory.SubFactory(VariantFactory)
    quantity = factory.Faker("random_int", min=1, max=10)
    sku_at_purchase = factory.LazyAttribute(lambda o: o.variant.sku)
    price_at_purchase = factory.LazyAttribute(lambda o: o.variant.price)
    product_name_at_purchase = factory.LazyAttribute(lambda o: o.variant.product.name)
