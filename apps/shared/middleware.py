
from django.utils.deprecation import MiddlewareMixin
from apps.memberships.models import Membership


class TenantContextMiddleware(MiddlewareMixin):
    HEADER = 'HTTP_X_OFFICE_ID'

    def process_request(self, request):
        request.organization = None
        request.office = None
        request.membership = None
        request.effective_perms = set()
        request.available_memberships = []
        request.office_selection_required = False

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return

        memberships = list(
            Membership.objects.filter(user=user, is_active=True)
            .select_related('organization', 'office', 'local_role')
            .prefetch_related('groups__permissions__content_type')
            .order_by('id')
        )
        request.available_memberships = memberships
        if not memberships:
            request.session.pop('org_id', None)
            request.session.pop('office_id', None)
            return

        org_ids = {m.organization_id for m in memberships}
        if len(org_ids) != 1:
            # regra nova: usuário só pode estar em uma org; se estiver sujo, aborta contexto para evitar vazamento.
            request.session.pop('org_id', None)
            request.session.pop('office_id', None)
            return

        request.organization = memberships[0].organization
        request.session['org_id'] = request.organization.id

        org_level = next((m for m in memberships if m.office_id is None), None)
        office_memberships = [m for m in memberships if m.office_id]
        by_office = {m.office_id: m for m in office_memberships}

        raw_office = request.META.get(self.HEADER) or request.session.get('office_id')
        chosen_office_id = None
        if raw_office not in (None, ''):
            try:
                chosen_office_id = int(raw_office)
            except (TypeError, ValueError):
                chosen_office_id = None

        active = None
        if chosen_office_id is not None:
            active = by_office.get(chosen_office_id)
            if active:
                request.office = active.office
                request.session['office_id'] = active.office_id
            else:
                request.session.pop('office_id', None)

        if active is None:
            if len(office_memberships) == 1:
                active = office_memberships[0]
                request.office = active.office
                request.session['office_id'] = active.office_id
            else:
                request.session.pop('office_id', None)
                request.office_selection_required = len(office_memberships) > 1
                active = org_level or (office_memberships[0] if office_memberships else None)

        request.membership = active
        if active:
            if active.office_id is None:
                request.effective_perms = active.get_all_permissions()
            elif request.office and request.office.id == active.office_id:
                request.effective_perms = active.get_all_permissions()
            else:
                request.effective_perms = set()
