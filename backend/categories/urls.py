from rest_framework.routers import DefaultRouter
from django.urls import include, path

from categories.views import CategoryViewset


router = DefaultRouter()
router.register(r"categories", CategoryViewset, basename="category")

urlpatterns = [path("", include(router.urls))]
