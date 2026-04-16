from rest_framework.routers import DefaultRouter
from orders.views import OrderViewset

router = DefaultRouter()
router.register("orders", OrderViewset, basename="order")
urlpatterns = router.urls
