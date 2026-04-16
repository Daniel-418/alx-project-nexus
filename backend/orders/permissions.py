# type: ignore
from rest_framework.permissions import BasePermission


class IsOrderOwner(BasePermission):
    message = "You do not have permission to access this order."

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff


class CanCancelOrder(BasePermission):
    message = "Only order owners and staff can cancel orders"

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if obj.user is not None:
            return request.user.is_authenticated and obj.user == request.user
        token = request.data.get("guest_token")
        return token is not None and str(obj.guest_token) == str(token)
