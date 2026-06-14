from django.urls import path
from rest_framework_nested.routers import NestedDefaultRouter

from orders.urls import router as orders_router
from payments.views import PaymentViewset, PaymentWebhook

router = NestedDefaultRouter(orders_router, "orders", lookup="order")
router.register("payments", PaymentViewset, basename="order-payment")

# The webhook URL must be listed before router.urls so it isn't swallowed by
# the nested router's pattern matching.  Full path: POST /api/payments/webhook/
urlpatterns = [
    path("payments/webhook/", PaymentWebhook.as_view(), name="payment-webhook"),
] + router.urls
