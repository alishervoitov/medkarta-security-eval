from django.conf import settings
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "admin")


class MedicalRecordObjectPermission(permissions.BasePermission):
    """Patients read only their own records; doctors and admins read all."""

    def has_object_permission(self, request, view, obj):
        u = request.user
        if u.role in ("doctor", "admin"):
            return True
        if "F4" in settings.FAULTS:  # FAULT F4: ownership check missing
            return request.method in permissions.SAFE_METHODS
        return obj.patient.user_id == u.id and request.method in permissions.SAFE_METHODS
