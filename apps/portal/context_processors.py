
from apps.portal.models import OfficePreference, ActivityLog
from apps.shared.permissions import get_context_perms


def portal_context(request):
    perms_ctx = get_context_perms(request)
    ctx = {
        'portal_body_class': 'hold-transition dark-mode sidebar-mini layout-fixed layout-navbar-fixed layout-footer-fixed',
        'current_office': getattr(request, 'office', None),
        'current_org': getattr(request, 'organization', None),
        'membership': getattr(request, 'membership', None),
        'office_choices': [],
        'membership_perms': perms_ctx,
        'portal_perms': perms_ctx,  # compat templates antigos
        'user_role': getattr(getattr(request, 'membership', None), 'role', None),
    }
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return ctx

    office_map = {}
    for m in (getattr(request, 'available_memberships', []) or []):
        if m.office_id and m.office and getattr(m.office, 'is_active', True):
            office_map[m.office_id] = m.office
    if len(office_map) > 1:
        ctx['office_choices'] = sorted(office_map.values(), key=lambda o: o.name.lower())

    office = getattr(request, 'office', None)
    if office:
        pref, _ = OfficePreference.objects.get_or_create(office=office)
        if pref.theme == 'light':
            ctx['portal_body_class'] = 'hold-transition sidebar-mini layout-fixed layout-navbar-fixed layout-footer-fixed'

    try:
        ctx['navbar_activity'] = ActivityLog.objects.filter(office=office)[:5] if office else []
    except Exception:
        ctx['navbar_activity'] = []
    return ctx
