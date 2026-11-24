from rest_framework.permissions import BasePermission

from .models import role_of


class IsMentor(BasePermission):
    message = "Solo disponible para mentores"

    def has_permission(self, request, view):
        return request.user.is_authenticated and role_of(request.user) == "mentor"
