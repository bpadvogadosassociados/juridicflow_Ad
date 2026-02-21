from apps.portal.models import OfficePreference
from apps.portal.models import ActivityLog
from apps.memberships.models import Membership

def portal_context(request):
    ctx = {
        "portal_body_class": "hold-transition dark-mode sidebar-mini layout-fixed layout-navbar-fixed layout-footer-fixed",
        "current_office": getattr(request, "office", None),
        "current_org": getattr(request, "organization", None),
        "membership": getattr(request, "membership", None),
        "office_choices": [],
    }
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return ctx

    membership = getattr(request, "membership", None)
    org = getattr(request, "organization", None)
    office = getattr(request, "office", None)

    if membership and org:
        if membership.role == "org_admin":
            ctx["office_choices"] = list(org.offices.filter(is_active=True).order_by("name"))
        else:
            from apps.memberships.models import Membership as M
            user_offices = list(
                M.objects.filter(
                    user=user, organization=org, is_active=True, office__isnull=False
                ).values_list("office_id", flat=True)
            )
            if len(set(user_offices)) > 1:
                from apps.offices.models import Office
                ctx["office_choices"] = list(
                    Office.objects.filter(id__in=user_offices, is_active=True).order_by("name")
                )



    if office:
        pref, _ = OfficePreference.objects.get_or_create(office=office)
        if pref.theme == "light":
            ctx["portal_body_class"] = "hold-transition sidebar-mini layout-fixed layout-navbar-fixed layout-footer-fixed"
        elif pref.theme == "dark":
            ctx["portal_body_class"] = "hold-transition dark-mode sidebar-mini layout-fixed layout-navbar-fixed layout-footer-fixed"
        else:
            ctx["portal_body_class"] = "hold-transition dark-mode sidebar-mini layout-fixed layout-navbar-fixed layout-footer-fixed"

    # últimas atividades para dropdown (pequeno resumo)
    try:
        if office:
            ctx["navbar_activity"] = ActivityLog.objects.filter(office=office)[:5]
        else:
            ctx["navbar_activity"] = []
    except Exception:
        ctx["navbar_activity"] = []
    return ctx
