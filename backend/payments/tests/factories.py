# type: ignore
import factory

from orders.tests.factories import OrderFactory
from payments.models import Payment


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    # SubFactory creates a full delivery Order (with shipping address) by
    # default, satisfying Order.clean() without any extra arguments.
    order = factory.SubFactory(OrderFactory)
    method = Payment.Method.PAYSTACK
    status = Payment.Status.PENDING
    currency = "NGN"
    price = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    transaction_id = None
    paid_at = None
