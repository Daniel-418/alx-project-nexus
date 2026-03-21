# type: ignore
import uuid
from django.db import models
from django.utils import timezone
from django.db.models import Max, constraints


# changes behaviour of the default queryset returned by Model.objects.all()
# by excluding objects that have been soft deleted
class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


# mixin that implements soft delete logic to be implmented in Product and Variant
# and product images
class SoftDeleteMixin(models.Model):
    deleted_at = models.DateTimeField(blank=True, null=True)
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def delete(self, using=None, keep_parents: bool = False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    class Meta:
        abstract = True


class Product(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    price = models.DecimalField(decimal_places=2, max_digits=15)
    name = models.CharField(max_length=50)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        self.variants.all().update(deleted_at=timezone.now())
        self.product_images.all().update(deleted_at=timezone.now())
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name}"


class OptionType(models.Model):
    option_type = models.CharField(max_length=25, unique=True)

    def __str__(self) -> str:
        return self.option_type

    def save(self, *args, **kwargs):
        if self.option_type:
            self.option_type = self.option_type.strip().upper()

        super().save(*args, **kwargs)


class OptionValue(models.Model):
    value = models.CharField(max_length=25)
    option_type = models.ForeignKey(OptionType, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["option_type", "value"], name="unique_option_value_combination"
            )
        ]

    def save(self, *args, **kwargs):
        if self.value:
            self.value = self.value.strip().lower()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.option_type}: {self.value}"


class ProductImage(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    product = models.ForeignKey(
        Product,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="product_images",
    )
    image = models.ImageField(upload_to="products/images/")
    alt_text = models.CharField(max_length=250)
    is_feature = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        # Partial unique index: only active (non-deleted) images must have unique
        # display_order within their scope. Soft-deleted images release their slot.
        constraints = [
            models.UniqueConstraint(
                fields=["product", "display_order"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_product_display_order",
            ),
        ]
        ordering = ["display_order"]

    def restore(self):
        conflict = ProductImage.objects.filter(
            product=self.product,
            display_order=self.display_order,
        ).exists()

        if conflict:
            self.display_order = self._get_next_display_order()
            self.save(update_fields=["display_order"])

        super().restore()

    def _get_next_display_order(self):
        qs = ProductImage.all_objects.filter(product=self.product)
        last_order = qs.aggregate(Max("display_order"))["display_order__max"]
        return (last_order or 0) + 1

    # auto increments display_order as a new image is created
    def save(self, *args, **kwargs):
        if self.display_order is None:
            self.display_order = self._get_next_display_order()

        super().save(*args, **kwargs)


class Variant(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    product = models.ForeignKey(
        Product, related_name="variants", on_delete=models.CASCADE
    )
    option_values = models.ManyToManyField(
        OptionValue, related_name="variants", blank=True
    )
    images = models.ManyToManyField(ProductImage, related_name="variants", blank=True)
    sku = models.CharField(max_length=225, unique=True)
    stock = models.IntegerField(default=0)
    is_master = models.BooleanField(default=False)
    price = models.DecimalField(decimal_places=2, max_digits=15)
    created_at = models.DateTimeField(auto_now_add=True)
