# type: ignore
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.views import Response
from rest_framework import status

from core.permissions import CanManageCatalog
from core.views import BaseCatalogViewset, RestoreMixin
from products.models import Product, ProductImage, Variant, OptionType, OptionValue
from products.serializers import (
    ProductImageInputSerializer,
    ProductImageOutputSerializer,
    ProductInputSerializer,
    ProductOutputSerializer,
    VariantImagesSerializer,
    VariantInputSerializer,
    VariantOutputSerializer,
    OptionTypeSerializer,
    OptionValueInputSerializer,
    OptionValueSerializer,
)


class OptionTypeViewset(BaseCatalogViewset):
    queryset = OptionType.objects.all()
    input_serializer_class = OptionTypeSerializer
    output_serializer_class = OptionTypeSerializer


class OptionValueViewset(BaseCatalogViewset):
    queryset = OptionValue.objects.all()
    input_serializer_class = OptionValueInputSerializer
    output_serializer_class = OptionValueSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["option_type"]


class ProductImageViewset(RestoreMixin, BaseCatalogViewset):
    queryset = ProductImage.objects.all()
    input_serializer_class = ProductImageInputSerializer
    output_serializer_class = ProductImageOutputSerializer

    # inject product_id into context so display_order validation has access to it
    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", self.get_serializer_context())
        kwargs["context"]["product_id"] = self.kwargs.get("product_pk")
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        product_id = self.kwargs.get("product_pk")
        get_object_or_404(Product, id=product_id)
        return ProductImage.objects.filter(product_id=product_id)

    def perform_create(self, serializer):
        product_id = self.kwargs.get("product_pk")
        get_object_or_404(Product, id=product_id)
        return serializer.save(product_id=product_id)


class ProductViewset(RestoreMixin, BaseCatalogViewset):
    queryset = Product.objects.all()
    input_serializer_class = ProductInputSerializer
    output_serializer_class = ProductOutputSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(categories__id=category)
        return qs


class VariantViewset(RestoreMixin, BaseCatalogViewset):
    queryset = Variant.objects.all()
    input_serializer_class = VariantInputSerializer
    output_serializer_class = VariantOutputSerializer

    # inject product_id into context so image and is_master validation have access to it
    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", self.get_serializer_context())
        kwargs["context"]["product_id"] = self.kwargs.get("product_pk")
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        product_id = self.kwargs.get("product_pk")
        get_object_or_404(Product, id=product_id)
        return Variant.objects.filter(product_id=product_id)

    def perform_create(self, serializer):
        product_id = self.kwargs.get("product_pk")
        get_object_or_404(Product, id=product_id)
        return serializer.save(product_id=product_id)

    # extend permissions to cover the images action
    def get_permissions(self):
        if self.action == "images":
            return [CanManageCatalog()]
        return super().get_permissions()

    # add or remove images from a variant, post to add delete to remove
    @action(methods=["post", "delete"], detail=True, url_path="images")
    def images(self, request, pk=None, product_pk=None):
        variant = self.get_object()
        serializer = VariantImagesSerializer(
            data=request.data, context={"product_id": str(product_pk)}
        )
        serializer.is_valid(raise_exception=True)
        images = serializer.validated_data["images"]

        if request.method == "POST":
            variant.images.add(*images)
        else:
            variant.images.remove(*images)

        return Response(VariantOutputSerializer(variant).data)
