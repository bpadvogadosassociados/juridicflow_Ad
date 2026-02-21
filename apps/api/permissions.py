from rest_framework.permissions import BasePermission

def _m(request):
    return getattr(request, "membership", None)

class IsInTenant(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, "organization", None) and _m(request))

class IsOrgAdmin(BasePermission):
    def has_permission(self, request, view):
        m = _m(request)
        return bool(m and m.role == "org_admin" and m.office_id is None)

class IsOfficeAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        m = _m(request)
        return bool(m and m.role in ("org_admin", "office_admin"))
