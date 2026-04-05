# type: ignore
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cart.permissions import IsCartOwner
from cart.models import Cart, CartItem
from cart.serializers import (
    CartInputSerializer,
    CartOutputSerializer,
    CartItemInputSerializer,
    CartItemOutputSerializer,
    MergeSerializer,
)
from core.views import DualSerializerMixin


class CartViewset(DualSerializerMixin, viewsets.ModelViewSet):
    input_serializer_class = CartInputSerializer
    output_serializer_class = CartOutputSerializer
    permission_classes = [IsCartOwner]
    # PUT and PATCH are disabled — CartInputSerializer has no writable fields
    http_method_names = ["get", "post", "delete", "head", "options"]

    # scope to the requesting user's carts — guests are scoped by session_id header
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Cart.objects.filter(user=self.request.user)
        session_id = self.request.headers.get("X-Cart-Session")
        return Cart.objects.filter(session_id=session_id)

    # link the cart to the authenticated user on creation; guest carts get a 30-day TTL
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            return serializer.save(user=self.request.user)
        return serializer.save(expires_at=timezone.now() + timedelta(days=30))

    # delete all items in the cart without deleting the cart itself
    @action(methods=["post"], detail=True, url_path="clear")
    def clear(self, request, pk=None):
        cart = self.get_object()
        cart.items.all().delete()
        return Response(CartOutputSerializer(cart).data)

    # merge a guest cart (identified by session_id in the request body) into the
    # authenticated user's target cart (identified by the URL pk)
    @action(
        methods=["post"],
        detail=True,
        url_path="merge",
        permission_classes=[IsAuthenticated],
    )
    def merge(self, request, pk=None):
        target_cart = self.get_object()

        serializer = MergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        guest_cart = get_object_or_404(
            Cart,
            session_id=serializer.validated_data["session_id"],
            user__isnull=True,
        )

        for guest_item in guest_cart.items.select_related("variant").all():
            variant = guest_item.variant
            try:
                target_item = CartItem.objects.get(cart=target_cart, variant=variant)
                # variant already in target cart — add quantities, clamp to stock
                target_item.quantity = min(
                    target_item.quantity + guest_item.quantity, variant.stock
                )
                target_item.save(update_fields=["quantity"])
            except CartItem.DoesNotExist:
                # variant not in target cart — reassign the item in-place
                guest_item.cart = target_cart
                guest_item.save(update_fields=["cart"])

        guest_cart.delete()
        target_cart.refresh_from_db()
        return Response(CartOutputSerializer(target_cart).data, status=status.HTTP_200_OK)


class CartItemViewset(DualSerializerMixin, viewsets.ModelViewSet):
    input_serializer_class = CartItemInputSerializer
    output_serializer_class = CartItemOutputSerializer
    permission_classes = [IsCartOwner]

    # fetch the cart from the nested URL, filtered by ownership — returns 404 if
    # the cart doesn't exist or doesn't belong to the requesting user/session
    def _get_owned_cart(self):
        cart_id = self.kwargs.get("cart_pk")
        if self.request.user.is_authenticated:
            return get_object_or_404(Cart, id=cart_id, user=self.request.user)
        session_id = self.request.headers.get("X-Cart-Session")
        return get_object_or_404(Cart, id=cart_id, session_id=session_id)

    # scope items to the owned cart so users can't read each other's cart contents
    def get_queryset(self):
        cart = self._get_owned_cart()
        return CartItem.objects.filter(cart=cart)

    # if the variant already exists in the cart, increment its quantity rather than
    # erroring — stock is validated against the total quantity in both cases
    def perform_create(self, serializer):
        cart = self._get_owned_cart()
        variant = serializer.validated_data["variant"]
        quantity = serializer.validated_data["quantity"]

        try:
            item = CartItem.objects.get(cart=cart, variant=variant)
            new_quantity = item.quantity + quantity
            if new_quantity > variant.stock:
                raise serializers.ValidationError(
                    {"quantity": f"Only {variant.stock} units available."}
                )
            item.quantity = new_quantity
            item.save(update_fields=["quantity"])
        except CartItem.DoesNotExist:
            if quantity > variant.stock:
                raise serializers.ValidationError(
                    {"quantity": f"Only {variant.stock} units available."}
                )
            item = serializer.save(cart=cart)

        return item

    def perform_update(self, serializer):
        variant = serializer.instance.variant
        new_quantity = serializer.validated_data.get(
            "quantity", serializer.instance.quantity
        )
        if new_quantity > variant.stock:
            raise serializers.ValidationError(
                {"quantity": f"Only {variant.stock} units available."}
            )
        serializer.save()

    # override create to return 200 when an existing item is incremented rather
    # than 201 — no new resource was created in that case
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # snapshot existence before the upsert so we know which status code to return
        cart = self._get_owned_cart()
        variant = serializer.validated_data["variant"]
        already_exists = CartItem.objects.filter(cart=cart, variant=variant).exists()

        instance = self.perform_create(serializer)
        output_serializer = self.output_serializer_class(instance)
        status_code = status.HTTP_200_OK if already_exists else status.HTTP_201_CREATED
        return Response(output_serializer.data, status=status_code)
