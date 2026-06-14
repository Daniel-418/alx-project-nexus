# type: ignore
import hashlib
import hmac
import json
import uuid
import pytest
from unittest.mock import Mock, patch

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.tests.fixtures import (
    standard_user_client,
    staff_client,
    anonymous_user,
    pytestmark,
)
from orders.models import Order
from orders.tests.factories import OrderFactory
from payments.models import Payment
from payments.tests.factories import PaymentFactory

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Webhook helpers
# ---------------------------------------------------------------------------


def _sign(payload_bytes: bytes) -> str:
    """Compute the HMAC-SHA512 signature the same way Paystack does."""
    secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")
    return hmac.new(secret, payload_bytes, hashlib.sha512).hexdigest()


def _payload(event: str, reference: str, **extra) -> bytes:
    """Return JSON bytes for a Paystack webhook payload.

    Extra keyword arguments are merged into the ``data`` dict so callers can
    include fields like ``amount`` or ``id`` without changing the signature.
    """
    return json.dumps(
        {"event": event, "data": {"reference": reference, **extra}}
    ).encode("utf-8")


@pytest.fixture
def webhook_client():
    # An unauthenticated client — the webhook endpoint is open to Paystack,
    # not to our users.
    return APIClient()


WEBHOOK_URL = "/api/payments/webhook/"


@pytest.mark.describe("PaymentViewset — create")
class TestPaymentCreate:
    @pytest.mark.it("paystack payment creates payment and returns authorization_url")
    def test_paystack_payment_creates_and_returns_authorization_url(
        self, standard_user_client
    ):
        order = OrderFactory(user=standard_user_client.user)
        url = reverse("order-payment-list", kwargs={"order_pk": str(order.id)})

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/1234",
                "reference": "ref_12345",
            },
        }

        with patch("payments.views.requests.post", return_value=mock_response):
            response = standard_user_client.post(
                url, data={"method": "paystack"}, format="json"
            )

        assert response.status_code == 201
        assert "authorization_url" in response.data
        assert Payment.objects.get(order=order).transaction_id == "ref_12345"


# ---------------------------------------------------------------------------
# Webhook — happy paths
# ---------------------------------------------------------------------------


@pytest.mark.describe("PaymentWebhook — charge.success")
class TestPaymentWebhookChargeSuccess:
    @pytest.mark.it(
        "valid charge.success marks payment COMPLETED, sets paid_at, and confirms the order"
    )
    def test_charge_success_completes_payment_and_confirms_order(self, webhook_client):
        payment = PaymentFactory(status=Payment.Status.PENDING)
        # amount must match: Paystack sends kobo (smallest unit), so multiply by 100.
        body = _payload(
            "charge.success",
            str(payment.id),
            amount=int(payment.price * 100),
            id="ps_txn_happy_path",
        )

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=_sign(body),
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.COMPLETED
        assert payment.paid_at is not None
        assert payment.transaction_id == "ps_txn_happy_path"
        payment.order.refresh_from_db()
        assert payment.order.status == Order.OrderStatus.CONFIRMED


@pytest.mark.describe("PaymentWebhook — charge.failed")
class TestPaymentWebhookChargeFailed:
    @pytest.mark.it("valid charge.failed marks payment FAILED")
    def test_charge_failed_marks_payment_failed(self, webhook_client):
        payment = PaymentFactory(status=Payment.Status.PENDING)
        body = _payload("charge.failed", str(payment.id))

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=_sign(body),
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.FAILED


# ---------------------------------------------------------------------------
# Webhook — signature verification
# ---------------------------------------------------------------------------


@pytest.mark.describe("PaymentWebhook — signature verification")
class TestPaymentWebhookSignatureVerification:
    @pytest.mark.it("wrong signature value returns 400")
    def test_wrong_signature_returns_400(self, webhook_client):
        payment = PaymentFactory()
        body = _payload("charge.success", str(payment.id))
        # 128 hex characters — right length, wrong value.
        bad_sig = "deadbeef" * 16

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=bad_sig,
        )

        assert response.status_code == 400

    @pytest.mark.it("missing X-Paystack-Signature header returns 400")
    def test_missing_signature_header_returns_400(self, webhook_client):
        payment = PaymentFactory()
        body = _payload("charge.success", str(payment.id))

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            # No HTTP_X_PAYSTACK_SIGNATURE — omitted entirely.
        )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Webhook — graceful handling
# ---------------------------------------------------------------------------


@pytest.mark.describe("PaymentWebhook — graceful handling")
class TestPaymentWebhookGracefulHandling:
    @pytest.mark.it("unknown reference returns 200 without raising")
    def test_unknown_reference_returns_200(self, webhook_client):
        # A valid UUID that doesn't match any Payment in the database.
        body = _payload("charge.success", str(uuid.uuid4()))

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=_sign(body),
        )

        assert response.status_code == 200

    @pytest.mark.it("unknown event type returns 200 and leaves payment unchanged")
    def test_unknown_event_leaves_payment_unchanged(self, webhook_client):
        payment = PaymentFactory(status=Payment.Status.PENDING)
        # An event type the view doesn't handle — e.g. a future Paystack event.
        body = _payload("refund.processed", str(payment.id))

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=_sign(body),
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PENDING

    @pytest.mark.it("already-completed payment is not re-processed (idempotent)")
    def test_already_completed_payment_is_not_reprocessed(self, webhook_client):
        original_paid_at = timezone.now()
        payment = PaymentFactory(
            status=Payment.Status.COMPLETED,
            paid_at=original_paid_at,
        )
        body = _payload("charge.success", str(payment.id))

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=_sign(body),
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.COMPLETED
        # paid_at must not have been overwritten by the second delivery.
        assert abs((payment.paid_at - original_paid_at).total_seconds()) < 1


# ---------------------------------------------------------------------------
# Staff manual approval
# ---------------------------------------------------------------------------


def _approve_url(payment):
    return reverse(
        "order-payment-approve",
        kwargs={"order_pk": str(payment.order.id), "pk": str(payment.id)},
    )


@pytest.mark.describe("PaymentViewset — approve")
class TestPaymentApprove:
    @pytest.mark.it("staff can approve a pending cash payment")
    def test_staff_approves_pending_cash_payment(self, staff_client):
        payment = PaymentFactory(
            method=Payment.Method.CASH, status=Payment.Status.PENDING
        )

        response = staff_client.post(_approve_url(payment))

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.COMPLETED
        assert payment.paid_at is not None
        payment.order.refresh_from_db()
        assert payment.order.status == Order.OrderStatus.CONFIRMED

    @pytest.mark.it("staff can approve a pending bank transfer payment")
    def test_staff_approves_pending_bank_transfer_payment(self, staff_client):
        payment = PaymentFactory(
            method=Payment.Method.BANK_TRANSFER, status=Payment.Status.PENDING
        )

        response = staff_client.post(_approve_url(payment))

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.COMPLETED
        assert payment.paid_at is not None

    @pytest.mark.it("approving a Paystack payment returns 400")
    def test_cannot_approve_paystack_payment(self, staff_client):
        # Paystack payments are confirmed by the webhook — manual approval
        # would bypass the actual payment verification.
        payment = PaymentFactory(
            method=Payment.Method.PAYSTACK, status=Payment.Status.PENDING
        )

        response = staff_client.post(_approve_url(payment))

        assert response.status_code == 400

    @pytest.mark.it("approving an already-completed payment returns 400")
    def test_cannot_approve_already_completed_payment(self, staff_client):
        payment = PaymentFactory(
            method=Payment.Method.CASH, status=Payment.Status.COMPLETED
        )

        response = staff_client.post(_approve_url(payment))

        assert response.status_code == 400

    @pytest.mark.it("non-staff user cannot approve a payment")
    def test_non_staff_cannot_approve(self, standard_user_client):
        payment = PaymentFactory(
            method=Payment.Method.CASH, status=Payment.Status.PENDING
        )

        response = standard_user_client.post(_approve_url(payment))

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Amount verification
# ---------------------------------------------------------------------------


@pytest.mark.describe("PaymentWebhook — amount verification")
class TestPaymentWebhookAmountVerification:
    @pytest.mark.it("charge.success with correct amount completes the payment")
    def test_correct_amount_completes_payment(self, webhook_client):
        payment = PaymentFactory(status=Payment.Status.PENDING)
        body = _payload(
            "charge.success",
            str(payment.id),
            amount=int(payment.price * 100),
        )

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=_sign(body),
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.COMPLETED

    @pytest.mark.it(
        "charge.success with mismatched amount marks payment FAILED and returns 200"
    )
    def test_mismatched_amount_marks_payment_failed(self, webhook_client):
        payment = PaymentFactory(status=Payment.Status.PENDING)
        # Send one kobo less than the expected amount — a partial payment.
        wrong_amount = int(payment.price * 100) - 1

        body = _payload("charge.success", str(payment.id), amount=wrong_amount)

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=_sign(body),
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.FAILED
        payment.order.refresh_from_db()
        assert payment.order.status != Order.OrderStatus.CONFIRMED

    @pytest.mark.it("charge.success with missing amount marks payment FAILED")
    def test_missing_amount_marks_payment_failed(self, webhook_client):
        # No 'amount' key in data at all — treat as mismatch (None != int).
        payment = PaymentFactory(status=Payment.Status.PENDING)
        body = _payload("charge.success", str(payment.id))

        response = webhook_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=_sign(body),
        )

        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.FAILED


# ---------------------------------------------------------------------------
# Duplicate payment prevention
# ---------------------------------------------------------------------------


@pytest.mark.describe("PaymentViewset — duplicate prevention")
class TestPaymentDuplicatePrevention:
    @pytest.mark.it("cannot create a second payment when a PENDING one already exists")
    def test_cannot_create_second_pending_payment(self, standard_user_client):
        order = OrderFactory(user=standard_user_client.user)
        PaymentFactory(order=order, status=Payment.Status.PENDING)
        url = reverse("order-payment-list", kwargs={"order_pk": str(order.id)})

        response = standard_user_client.post(
            url, data={"method": "cash"}, format="json"
        )

        assert response.status_code == 400
        assert "already has an active" in response.data["detail"]
        assert Payment.objects.filter(order=order).count() == 1

    @pytest.mark.it("cannot create a payment when a COMPLETED one already exists")
    def test_cannot_create_payment_when_completed_exists(self, standard_user_client):
        order = OrderFactory(user=standard_user_client.user)
        PaymentFactory(order=order, status=Payment.Status.COMPLETED)
        url = reverse("order-payment-list", kwargs={"order_pk": str(order.id)})

        response = standard_user_client.post(
            url, data={"method": "cash"}, format="json"
        )

        assert response.status_code == 400
        assert Payment.objects.filter(order=order).count() == 1

    @pytest.mark.it("can create a new payment after a FAILED one (retry is allowed)")
    def test_can_create_payment_after_failed(self, standard_user_client):
        order = OrderFactory(user=standard_user_client.user)
        PaymentFactory(order=order, status=Payment.Status.FAILED)
        url = reverse("order-payment-list", kwargs={"order_pk": str(order.id)})

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/retry",
                "reference": "ref_retry",
            },
        }

        with patch("payments.views.requests.post", return_value=mock_response):
            response = standard_user_client.post(
                url, data={"method": "paystack"}, format="json"
            )

        assert response.status_code == 201
        assert Payment.objects.filter(order=order).count() == 2


# ---------------------------------------------------------------------------
# BUG TESTS — these tests are expected to FAIL with the current code.
# They document the correct behaviour and prove the bugs exist.
# ---------------------------------------------------------------------------


@pytest.mark.describe("PaymentViewset — retrieve [BUG]")
class TestPaymentRetrieve:
    @pytest.mark.it("owner can retrieve their own payment")
    def test_owner_can_retrieve_payment(self, standard_user_client):
        order = OrderFactory(user=standard_user_client.user)
        payment = PaymentFactory(order=order)
        url = reverse(
            "order-payment-detail",
            kwargs={"order_pk": str(order.id), "pk": str(payment.id)},
        )

        response = standard_user_client.get(url)

        # BUG: get_permissions() returns [IsOrderOwner()] for retrieve.
        # DRF's RetrieveModelMixin calls get_object(), which calls
        # check_object_permissions(request, payment).  IsOrderOwner.has_object_permission
        # then evaluates `obj.user` — but Payment has no `.user` field.
        # AttributeError propagates up and Django returns a 500.
        assert response.status_code == 200


@pytest.mark.describe("PaymentViewset — list [BUG]")
class TestPaymentList:
    @pytest.mark.it("unauthenticated caller cannot list payments for an order")
    def test_unauthenticated_cannot_list_payments(self, anonymous_user):
        order = OrderFactory()
        PaymentFactory(order=order, status=Payment.Status.PENDING)
        url = reverse("order-payment-list", kwargs={"order_pk": str(order.id)})

        response = anonymous_user.get(url)

        # BUG: IsOrderOwner only overrides has_object_permission, not has_permission.
        # DRF's default has_permission returns True for everyone, so the view-level
        # gate is wide open.  The list action never calls check_object_permissions
        # (no single object to check), so has_object_permission never fires either.
        # An anonymous caller receives a 200 with the full payment list.
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Guest payment creation — all three tests define desired final behaviour.
#
# TODAY they all return 401 and therefore FAIL.  Why 401 instead of 403?
# JWT authentication runs before DRF permission checking.  When no valid
# token is present, DRF sees that authenticators exist but none succeeded,
# and raises NotAuthenticated (401) before has_permission is ever evaluated.
#
# The fix requires two coordinated changes:
#   1. PaymentViewset.get_permissions() must return [AllowAny()] for `create`
#      so the JWT auth short-circuit never fires for guest requests.
#   2. The create() method must then check guest_token from request.data
#      against order.guest_token, returning 403 when the token is absent or
#      wrong (mirrors the CanCancelOrder pattern in orders/permissions.py).
#
# After the fix: correct token → 201, wrong token → 403, no token → 403.
# ---------------------------------------------------------------------------


@pytest.mark.describe("PaymentViewset — guest payment creation")
class TestGuestPaymentCreate:
    @pytest.mark.it("guest with correct guest_token can create a payment")
    def test_guest_can_create_payment_with_correct_guest_token(self, anonymous_user):
        guest_token = uuid.uuid4()
        order = OrderFactory(user=None, guest_token=guest_token)
        url = reverse("order-payment-list", kwargs={"order_pk": str(order.id)})

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/guest",
                "reference": "ref_guest_ok",
            },
        }

        with patch("payments.views.requests.post", return_value=mock_response):
            response = anonymous_user.post(
                url,
                data={"method": "paystack", "guest_token": str(guest_token)},
                format="json",
            )

        # FAILS TODAY with 401 — JWT auth rejects the unauthenticated request
        # before create() is reached.
        assert response.status_code == 201
        assert "authorization_url" in response.data

    @pytest.mark.it("guest with wrong guest_token is rejected with 403")
    def test_guest_with_wrong_token_is_rejected(self, anonymous_user):
        order = OrderFactory(user=None, guest_token=uuid.uuid4())
        url = reverse("order-payment-list", kwargs={"order_pk": str(order.id)})

        response = anonymous_user.post(
            url,
            data={"method": "paystack", "guest_token": str(uuid.uuid4())},
            format="json",
        )

        # FAILS TODAY with 401.  After the fix: AllowAny lets the request
        # through; the explicit token check in create() returns 403.
        assert response.status_code == 403

    @pytest.mark.it("guest with no guest_token is rejected with 403")
    def test_guest_with_no_token_is_rejected(self, anonymous_user):
        order = OrderFactory(user=None, guest_token=uuid.uuid4())
        url = reverse("order-payment-list", kwargs={"order_pk": str(order.id)})

        response = anonymous_user.post(
            url,
            data={"method": "paystack"},
            format="json",
        )

        # FAILS TODAY with 401.  After the fix: AllowAny lets the request
        # through; the missing token in request.data returns 403.
        assert response.status_code == 403
