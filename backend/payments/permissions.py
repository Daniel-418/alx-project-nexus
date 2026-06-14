# type: ignore
from rest_framework.permissions import BasePermission


class IsPaymentOwner(BasePermission):
    """Guards list and retrieve — requires an authenticated user who owns the order."""

    message = "You do not have permission to access this payment."

    def has_permission(self, request, view):
        # View-level gate: closes the list/retrieve gap that exists when only
        # has_object_permission is defined (list never calls it — no single
        # object to check — so an anonymous caller would see a 200).
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # obj is always a Payment here.  Payment has no direct .user field;
        # ownership lives on the parent order.
        return obj.order.user == request.user or request.user.is_staff


class CanCreatePayment(BasePermission):
    """Guards create — allows staff, authenticated order owners, and guests with
    a valid guest_token.  No has_permission override so anonymous requests are
    not rejected at the view level; the real check happens in has_object_permission
    once the parent Order is in hand."""

    message = "You do not have permission to create a payment for this order."

    def has_object_permission(self, request, view, obj):
        # obj is the parent Order passed explicitly by PaymentViewset.create().
        if request.user.is_staff:
            return True
        if obj.user is not None:
            # Authenticated order: caller must own it.
            return request.user.is_authenticated and obj.user == request.user
        # Guest order: the guest_token in request.data must match.
        token = request.data.get("guest_token")
        return token is not None and str(obj.guest_token) == str(token)
