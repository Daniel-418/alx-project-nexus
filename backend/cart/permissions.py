from rest_framework.permissions import BasePermission
from cart.models import Cart


class IsCartOwner(BasePermission):
    """
    permission to check who can manage a cart. returns true if the request owns the cart.
    works for both Cart and CartItem objects — resolves the cart from whichever is passed.
    """

    message = "Cart does not belong to this session/user"

    # allow cart creation without a session — the session_id is returned in the response
    # for all other actions, guests must supply X-Cart-Session to prove ownership
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return True
        if view.action == "create":
            return True
        return bool(request.headers.get("X-Cart-Session"))

    # resolves the cart from either a Cart or CartItem instance so the same
    # permission class works on both CartViewset and CartItemViewset
    def has_object_permission(self, request, view, obj):
        cart = obj if isinstance(obj, Cart) else obj.cart
        if request.user.is_authenticated:
            return cart.user == request.user
        session_id = request.headers.get("X-Cart-Session")
        return str(cart.session_id) == session_id
