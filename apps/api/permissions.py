
from rest_framework.permissions import BasePermission


def _m(request):
    return getattr(request, 'membership', None)


class IsInTenant(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, 'organization', None) and _m(request))


class HasMembershipViewPerms(BasePermission):
    message = 'Permissão insuficiente para este recurso.'

    def has_permission(self, request, view):
        if not _m(request):
            return False
        effective = getattr(request, 'effective_perms', set()) or set()
        perms = tuple(getattr(view, 'required_perms', ()) or ())
        require_all = bool(getattr(view, 'require_all', False))
        action = getattr(view, 'action', None)
        per_action = getattr(view, 'required_perms_map', None) or {}
        if action and action in per_action:
            perms = tuple(per_action.get(action) or ())
            require_all = bool((getattr(view, 'require_all_map', None) or {}).get(action, require_all))
        if not perms:
            return True
        return all(p in effective for p in perms) if require_all else any(p in effective for p in perms)


class IsOrgAdmin(BasePermission):
    def has_permission(self, request, view):
        effective = getattr(request, 'effective_perms', set()) or set()
        return bool(_m(request) and any(p in effective for p in ('memberships.change_membership','organizations.change_organization','offices.change_office')))


class IsOfficeAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        effective = getattr(request, 'effective_perms', set()) or set()
        return bool(_m(request) and any(p in effective for p in ('finance.change_feeagreement','finance.change_invoice','memberships.change_membership')))
