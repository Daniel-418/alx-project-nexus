# type: ignore
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.views import Response
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from products.models import Product, ProductImage, Variant, OptionType, OptionValue
from products.permissions import CanManageCatalog
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
from rest_framework import status


# restore mixin to use for models with soft delete logic
class RestoreMixin:
    @action(methods=["post"], detail=True)
    def restore(self, request, pk=None, **kwargs):
        model = self.queryset.model

        lookup_kwargs = {"pk": pk}

        if "product_pk" in kwargs:
            lookup_kwargs["product_id"] = kwargs["product_pk"]

        instance = get_object_or_404(model.all_objects, **lookup_kwargs)

        self.check_object_permissions(self.request, instance)

        instance.restore()
        instance.save()
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)

        return Response(serializer.data, status=status.HTTP_200_OK)


# base viewset that contains common logic across catalog related models
class BaseCatalogViewset(viewsets.ModelViewSet):
    # input and output serializer class to be overriden by children
    input_serializer_class = None
    output_serializer_class = None

    # use different serializers for input and output
    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.input_serializer_class
        return self.output_serializer_class

    # only staff can manipulate instances, anybody can view
    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "restore"]:
            return [CanManageCatalog()]
        return [AllowAny()]

    def perform_create(self, serializer):
        return serializer.save()

    # override create to use a separate serializer to output the the instance after creating
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instance = self.perform_create(serializer)

        output_serializer = self.output_serializer_class(instance)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    # override update to use a separate serializer to output the the instance after updating
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        output_serializer = self.output_serializer_class(instance)
        return Response(output_serializer.data)


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
