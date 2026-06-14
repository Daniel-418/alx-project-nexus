# type: ignore
import hashlib
import hmac
import json
import requests

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied

from core.permissions import CanManageCatalog
from core.views import DualSerializerMixin
from orders.models import Order
from payments.models import Payment
from payments.permissions import CanCreatePayment, IsPaymentOwner
from payments.serializers import PaymentInputSerializer, PaymentOutputSerializer


class PaymentViewset(
    DualSerializerMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    input_serializer_class = PaymentInputSerializer
    output_serializer_class = PaymentOutputSerializer

    def _get_order(self):
        return get_object_or_404(Order, pk=self.kwargs["order_pk"])

    # get only payments for a specific order
    def get_queryset(self):
        return Payment.objects.filter(order=self._get_order())

    def get_permissions(self):
        if self.action == "approve":
            return [CanManageCatalog()]
        if self.action == "create":
            return [CanCreatePayment()]
        return [IsPaymentOwner()]

    def permission_denied(self, request, message=None, code=None):
        # DRF's default permission_denied() raises 401 when authenticators exist
        # but none succeeded — its way of saying "maybe log in first".  For the
        # create action we support guests who intentionally have no JWT, so a
        # wrong or missing guest_token should be 403 (forbidden), not 401.
        if self.action == "create":
            raise DRFPermissionDenied(detail=message, code=code)
        super().permission_denied(request, message=message, code=code)

    # initialize a payment to paystack and return an authorization url
    def _initialize_paystack(self, payment):
        try:
            response = requests.post(
                "https://api.paystack.co/transaction/initialize",
                headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
                json={
                    "email": payment.order.contact_email,
                    "amount": int(payment.price * 100),
                    "reference": str(payment.id),
                },
                timeout=10,
            )
            data = response.json()
        except requests.RequestException:
            return None

        if not data.get("status"):
            return None

        payment.transaction_id = data["data"]["reference"]
        payment.save(update_fields=["transaction_id"])
        return data["data"]["authorization_url"]

    def create(self, request, *args, **kwargs):
        order = self._get_order()
        self.check_object_permissions(request, order)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # The duplicate check and INSERT are one atomic operation so two
        # concurrent requests can't both pass the check and each create a
        # PENDING payment for the same order.  The DB constraint is the final
        # backstop for any path that bypasses this guard.
        with transaction.atomic():
            existing = Payment.objects.filter(
                order=order,
                status__in=[Payment.Status.PENDING, Payment.Status.COMPLETED],
            ).first()
            if existing:
                return Response(
                    {
                        "detail": "This order already has an active or completed payment."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            payment = serializer.save(order=order, price=order.total)

        # Paystack initialization is a network call — keep it outside the
        # transaction so the DB connection isn't held open during the round-trip.
        authorization_url = None
        if payment.method == Payment.Method.PAYSTACK:
            authorization_url = self._initialize_paystack(payment)
            if authorization_url is None:
                payment.delete()
                return Response(
                    {"detail": "Failed to initialize payment with Paystack."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        output = self.output_serializer_class(payment)
        response_data = {**output.data}
        if authorization_url:
            response_data["authorization_url"] = authorization_url

        return Response(response_data, status=status.HTTP_201_CREATED)

    # Staff action for offline payment methods (cash, bank transfer) that have
    # no automated callback.  Paystack payments must go through the webhook
    # instead — approving them manually would bypass the actual payment check.
    @action(methods=["post"], detail=True, url_path="approve")
    def approve(self, request, order_pk=None, pk=None):
        # select_for_update() acquires a row-level lock on the payment row for
        # the duration of the transaction, so a concurrent webhook delivery and
        # a staff approval can't both process the same PENDING payment.
        with transaction.atomic():
            payment = get_object_or_404(
                Payment.objects.select_for_update().select_related("order"),
                pk=self.kwargs["pk"],
                order_id=self.kwargs["order_pk"],
            )

            if payment.method == Payment.Method.PAYSTACK:
                return Response(
                    {
                        "detail": "Paystack payments are confirmed automatically via webhook."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if payment.status != Payment.Status.PENDING:
                return Response(
                    {
                        "detail": f"Only pending payments can be approved. Current status: {payment.status}."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment.status = Payment.Status.COMPLETED
            payment.paid_at = timezone.now()
            payment.save(update_fields=["status", "paid_at"])

            payment.order.status = Order.OrderStatus.CONFIRMED
            payment.order.save(update_fields=["status"])

        return Response(
            self.output_serializer_class(payment).data, status=status.HTTP_200_OK
        )


class PaymentWebhook(APIView):
    # Paystack is an external server — it cannot send a JWT, so we skip DRF's
    # auth pipeline entirely. The request is authenticated via the HMAC-SHA512
    # signature that Paystack attaches to every delivery instead.
    authentication_classes = []
    permission_classes = [AllowAny]

    def _verify_signature(self, request) -> bool:
        # Django stores HTTP headers in META with the HTTP_ prefix and dashes
        # replaced by underscores, so X-Paystack-Signature → HTTP_X_PAYSTACK_SIGNATURE.
        signature = request.META.get("HTTP_X_PAYSTACK_SIGNATURE", "")
        if not signature:
            return False
        secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")
        # We read request.body (raw bytes) here rather than request.data because
        # the HMAC must be computed over the exact bytes Paystack sent.  DRF's
        # parser pipeline is lazy — it only runs when request.data is accessed —
        # so request.body is untouched at this point.
        computed = hmac.new(secret, request.body, hashlib.sha512).hexdigest()
        # compare_digest does a constant-time comparison, which prevents an
        # attacker from leaking the correct signature one byte at a time by
        # measuring how long the comparison takes.
        return hmac.compare_digest(computed, signature)

    def post(self, request, *args, **kwargs):
        if not self._verify_signature(request):
            return Response(
                {"detail": "Invalid signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            # Malformed JSON from a verified source — nothing we can do, but
            # returning 200 prevents Paystack from retrying indefinitely.
            return Response(status=status.HTTP_200_OK)

        event = payload.get("event")
        data = payload.get("data", {})
        reference = data.get("reference")

        if not reference:
            return Response(status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                # select_for_update() locks the payment row for the duration of
                # this transaction.  If a staff member is mid-approval on the
                # same payment, this call blocks until that transaction commits,
                # then re-reads the (now non-PENDING) status and exits cleanly.
                payment = (
                    Payment.objects.select_for_update()
                    .select_related("order")
                    .get(pk=reference)
                )

                # Idempotency: a second delivery of the same event is a no-op.
                if payment.status != Payment.Status.PENDING:
                    return Response(status=status.HTTP_200_OK)

                if event == "charge.success":
                    # Verify the settled amount matches what we initialized.
                    # A mismatch means a partial payment or a tampered payload —
                    # neither should advance the order.  We mark FAILED so staff
                    # can investigate; returning 200 prevents Paystack retrying.
                    received_amount = data.get("amount")
                    expected_amount = int(payment.price * 100)
                    if received_amount != expected_amount:
                        payment.status = Payment.Status.FAILED
                        payment.save(update_fields=["status"])
                        return Response(status=status.HTTP_200_OK)

                    payment.status = Payment.Status.COMPLETED
                    payment.paid_at = timezone.now()
                    # Store Paystack's own transaction ID alongside our reference
                    # so staff can look up the charge in the Paystack dashboard.
                    update_fields = ["status", "paid_at"]
                    paystack_txn_id = data.get("id")
                    if paystack_txn_id:
                        payment.transaction_id = str(paystack_txn_id)
                        update_fields.append("transaction_id")
                    payment.save(update_fields=update_fields)

                    order = payment.order
                    order.status = Order.OrderStatus.CONFIRMED
                    order.save(update_fields=["status"])

                elif event == "charge.failed":
                    payment.status = Payment.Status.FAILED
                    payment.save(update_fields=["status"])

                # Unrecognised event types do nothing — return 200 below.

        except (Payment.DoesNotExist, ValueError):
            # Unknown reference or non-UUID string — not our payment, ignore.
            pass

        return Response(status=status.HTTP_200_OK)
