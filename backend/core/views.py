# type: ignore
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.views import Response

from core.permissions import CanManageCatalog


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
