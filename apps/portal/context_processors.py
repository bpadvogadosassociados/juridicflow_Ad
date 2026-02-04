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

    if membership and org and membership.role == "org_admin" and office is None:
        # lista de escritórios para seleção
        ctx["office_choices"] = list(org.offices.all().order_by("name"))

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
