from rest_framework_nested.routers import NestedDefaultRouter
from rest_framework.routers import DefaultRouter
from django.urls import include, path
from products.views import (
    ProductImageViewset,
    ProductViewset,
    VariantViewset,
    OptionTypeViewset,
    OptionValueViewset,
)

router = DefaultRouter()
router.register(r"products", ProductViewset, basename="product")
router.register(r"option-types", OptionTypeViewset, basename="option-type")
router.register(r"option-values", OptionValueViewset, basename="option-value")

products_router = NestedDefaultRouter(router, r"products", lookup="product")
products_router.register(r"variants", VariantViewset, basename="product-variants")
products_router.register(r"images", ProductImageViewset, basename="product-images")

urlpatterns = [path("", include(router.urls)), path("", include(products_router.urls))]
