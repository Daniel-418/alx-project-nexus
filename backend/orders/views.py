# type: ignore
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.permissions import CanManageCatalog
from core.views import DualSerializerMixin
from orders.models import Order
from orders.permissions import CanCancelOrder, IsOrderOwner
from orders.serializers import OrderInputSerializer, OrderOutputSerializer


class OrderViewset(
    DualSerializerMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    input_serializer_class = OrderInputSerializer
    output_serializer_class = OrderOutputSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all().order_by("-created_at")
        if self.request.user.is_authenticated:
            return Order.objects.filter(user=self.request.user).order_by("-created_at")
        if self.action == "cancel":
            return Order.objects.filter(user=None).order_by("-created_at")
        return Order.objects.none()

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        if self.action == "retrieve":
            return [IsOrderOwner()]
        if self.action == "cancel":
            return [CanCancelOrder()]
        if self.action == "update_status":
            return [CanManageCatalog()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = serializer.validated_data["cart"]
        order = self.perform_create(serializer)
        cart.delete()
        output = self.output_serializer_class(order)
        return Response(output.data, status=status.HTTP_201_CREATED)

    # cancel pending or confirmed orders — other statuses are already in-flight or terminal and
    # can only be cancelled by staff
    @action(methods=["post"], detail=True, url_path="cancel")
    def cancel(self, request, pk=None):
        order = self.get_object()
        cancellable = {Order.OrderStatus.PENDING, Order.OrderStatus.CONFIRMED}

        if order.status not in cancellable:
            if not request.user.is_staff:
                return Response(
                    {"detail": "Only pending or confirmed orders can be cancelled."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        order.status = Order.OrderStatus.CANCELLED
        order.save(update_fields=["status"])
        return Response(OrderOutputSerializer(order).data, status=status.HTTP_200_OK)

    # staff-only action to advance an order through the fulfilment workflow
    @action(methods=["patch"], detail=True, url_path="status")
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get("status")
        if new_status not in Order.OrderStatus.values:
            return Response(
                {
                    "status": f"Invalid status. Choose from: {', '.join(Order.OrderStatus.values)}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = new_status
        order.save(update_fields=["status"])
        return Response(OrderOutputSerializer(order).data)
