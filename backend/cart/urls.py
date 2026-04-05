from rest_framework_nested.routers import NestedDefaultRouter
from rest_framework.routers import DefaultRouter
from django.urls import include, path
from cart.views import CartViewset, CartItemViewset

router = DefaultRouter()
router.register(r"carts", CartViewset, basename="cart")

cart_router = NestedDefaultRouter(router, r"carts", lookup="cart")
cart_router.register(r"cart_items", CartItemViewset, basename="cart-items")

urlpatterns = [path("", include(router.urls)), path("", include(cart_router.urls))]
