from django.utils.deprecation import MiddlewareMixin
from apps.memberships.models import Membership

class TenantContextMiddleware(MiddlewareMixin):
    HEADER = "HTTP_X_OFFICE_ID"

    def process_request(self, request):
        request.organization = None
        request.office = None
        request.membership = None

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return

        memberships = Membership.objects.filter(user=user, is_active=True).select_related("organization", "office")
        membership = memberships.filter(role="org_admin", office__isnull=True).first() or memberships.first()
        if not membership:
            return

        request.membership = membership
        request.organization = membership.organization

        if membership.office_id:
            request.office = membership.office
            return

        office_id = request.META.get(self.HEADER) or request.session.get("office_id")
        if office_id:
            try:
                request.office = membership.organization.offices.get(id=office_id)
            except Exception:
                request.office = None
