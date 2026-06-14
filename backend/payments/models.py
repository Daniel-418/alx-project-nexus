import uuid
from django.db import models
from django.db.models import Q
from orders.models import Order


class Payment(models.Model):
    class Method(models.TextChoices):
        PAYSTACK = "paystack", "Paystack"
        CASH = "cash", "Cash"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    order = models.ForeignKey(Order, related_name="payments", on_delete=models.PROTECT)
    method = models.CharField(
        max_length=50, choices=Method.choices, default=Method.PAYSTACK
    )
    status = models.CharField(
        max_length=50, choices=Status.choices, default=Status.PENDING
    )
    currency = models.CharField(max_length=3, default="NGN")
    price = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Partial unique index: only one payment per order may be in
            # PENDING or COMPLETED state at a time.  FAILED / CANCELLED /
            # REFUNDED payments are excluded so retries after failure are
            # possible.  This is the DB-level enforcement of the guard in
            # PaymentViewset.create — it catches any bypass (manual inserts,
            # future code paths that skip the application check, etc.).
            models.UniqueConstraint(
                fields=["order"],
                condition=Q(status__in=["pending", "completed"]),
                name="unique_active_payment_per_order",
            )
        ]
