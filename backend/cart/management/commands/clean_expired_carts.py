from django.core.management.base import BaseCommand
from django.utils import timezone
from cart.models import Cart


class Command(BaseCommand):
    help = "Deletes guest carts whose expires_at timestamp has passed."

    def handle(self, *args, **options):
        expired = Cart.objects.filter(
            expires_at__isnull=False,
            expires_at__lt=timezone.now(),
        )
        count, _ = expired.delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {count} expired guest cart(s).")
        )
