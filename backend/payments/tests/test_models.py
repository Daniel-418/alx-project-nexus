# type: ignore
import pytest
from django.db import IntegrityError, transaction

from orders.tests.factories import OrderFactory
from payments.models import Payment
from payments.tests.factories import PaymentFactory

pytestmark = pytest.mark.django_db


@pytest.mark.describe("Payment — defaults")
class TestPaymentDefaults:
    @pytest.mark.it("currency defaults to NGN")
    def test_default_currency(self):
        payment = PaymentFactory()
        assert payment.currency == "NGN"

    @pytest.mark.it("method defaults to PAYSTACK")
    def test_default_method(self):
        payment = PaymentFactory()
        assert payment.method == Payment.Method.PAYSTACK

    @pytest.mark.it("status defaults to PENDING")
    def test_default_status(self):
        payment = PaymentFactory()
        assert payment.status == Payment.Status.PENDING

    @pytest.mark.it("paid_at is null on creation")
    def test_paid_at_is_null_on_creation(self):
        payment = PaymentFactory()
        assert payment.paid_at is None

    @pytest.mark.it("transaction_id is null on creation")
    def test_transaction_id_is_null_on_creation(self):
        payment = PaymentFactory()
        assert payment.transaction_id is None


@pytest.mark.describe("Payment — unique_active_payment_per_order constraint")
class TestUniqueActivePaymentConstraint:
    @pytest.mark.it("blocks a second PENDING payment for the same order")
    def test_constraint_blocks_second_pending_payment(self):
        order = OrderFactory()
        PaymentFactory(order=order, status=Payment.Status.PENDING)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                PaymentFactory(order=order, status=Payment.Status.PENDING)

    @pytest.mark.it("blocks a second COMPLETED payment for the same order")
    def test_constraint_blocks_second_completed_payment(self):
        order = OrderFactory()
        PaymentFactory(order=order, status=Payment.Status.COMPLETED)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                PaymentFactory(order=order, status=Payment.Status.COMPLETED)

    @pytest.mark.it("blocks a PENDING payment when a COMPLETED one already exists")
    def test_constraint_blocks_pending_when_completed_exists(self):
        order = OrderFactory()
        PaymentFactory(order=order, status=Payment.Status.COMPLETED)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                PaymentFactory(order=order, status=Payment.Status.PENDING)

    @pytest.mark.it("allows multiple FAILED payments per order (retry path)")
    def test_multiple_failed_payments_are_allowed(self):
        order = OrderFactory()
        PaymentFactory(order=order, status=Payment.Status.FAILED)
        PaymentFactory(order=order, status=Payment.Status.FAILED)

        assert Payment.objects.filter(order=order).count() == 2

    @pytest.mark.it("allows a FAILED payment alongside a COMPLETED one")
    def test_failed_alongside_completed_is_allowed(self):
        order = OrderFactory()
        PaymentFactory(order=order, status=Payment.Status.COMPLETED)
        PaymentFactory(order=order, status=Payment.Status.FAILED)

        assert Payment.objects.filter(order=order).count() == 2
