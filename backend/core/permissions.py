from rest_framework.permissions import BasePermission


class CanManageCatalog(BasePermission):
    """
    permission to check for who can manage the store's catalog
    """

    message = "managing catalog is not allowed"

    # allow only staff users to proceed
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)
