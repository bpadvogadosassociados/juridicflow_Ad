
"""Compat layer enquanto views/templates migram para request.effective_perms."""
from apps.shared.permissions import require_role, require_action, require_membership_perm, membership_has_perm, get_context_perms


def portal_permissions(request):
    membership = getattr(request, 'membership', None)
    return {
        'user_role': getattr(membership, 'role', None),
        'user_role_display': membership.get_role_display() if membership else None,
        'portal_perms': get_context_perms(request),
    }
