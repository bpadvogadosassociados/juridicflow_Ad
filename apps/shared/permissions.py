
from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse


def _forbidden_response(request, message: str):
    accept = request.META.get("HTTP_ACCEPT", "")
    is_xhr = request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
    if "application/json" in accept or is_xhr:
        return JsonResponse({"error": "forbidden", "detail": message}, status=403)
    return HttpResponseForbidden(message)


def membership_has_perm(request, *perms, require_all=False):
    effective = getattr(request, "effective_perms", set()) or set()
    if not perms:
        return True
    return all(p in effective for p in perms) if require_all else any(p in effective for p in perms)


def require_membership_perm(*perms, require_all=False):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not getattr(request, "membership", None):
                return _forbidden_response(request, "Sem vínculo ativo no contexto.")
            if not membership_has_perm(request, *perms, require_all=require_all):
                return _forbidden_response(request, f"Permissão insuficiente. Requer: {', '.join(perms)}")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_context_perms(request):
    return {perm.replace('.', '_'): True for perm in (getattr(request, 'effective_perms', set()) or set())}


LEGACY_ACTION_MAP = {
    'process_view': ('processes.view_process',),
    'process_create': ('processes.add_process',),
    'process_edit': ('processes.change_process',),
    'process_delete': ('processes.delete_process',),
    'customer_view': ('customers.view_customer',),
    'customer_create': ('customers.add_customer',),
    'customer_edit': ('customers.change_customer',),
    'customer_delete': ('customers.delete_customer',),
    'customer_export': ('customers.view_customer',),
    'customer_import': ('customers.add_customer',),
    'document_view': ('documents.view_document',),
    'document_upload': ('documents.add_document',),
    'document_edit': ('documents.change_document',),
    'document_delete': ('documents.delete_document',),
    'deadline_view': ('deadlines.view_deadline',),
    'deadline_create': ('deadlines.add_deadline',),
    'deadline_edit': ('deadlines.change_deadline',),
    'deadline_delete': ('deadlines.delete_deadline',),
    'finance_view': ('finance.view_feeagreement', 'finance.view_invoice', 'finance.view_payment', 'finance.view_expense'),
    'finance_create': ('finance.add_feeagreement', 'finance.add_invoice', 'finance.add_payment', 'finance.add_expense'),
    'finance_edit': ('finance.change_feeagreement', 'finance.change_invoice', 'finance.change_payment', 'finance.change_expense'),
    'finance_delete': ('finance.delete_feeagreement', 'finance.delete_invoice', 'finance.delete_payment', 'finance.delete_expense'),
    'settings_view': ('organizations.view_organization',),
    'settings_edit': ('organizations.change_organization',),
    'team_view': ('memberships.view_membership',),
    'team_manage': ('memberships.add_membership', 'memberships.change_membership'),
}


def require_action(action: str):
    perms = LEGACY_ACTION_MAP.get(action)
    if not perms:
        perms = ('__missing_perm_mapping__',)
    return require_membership_perm(*perms, require_all=False)


_ROLE_TO_PERMS = {
    'intern': ('processes.view_process', 'customers.view_customer', 'documents.view_document', 'deadlines.view_deadline'),
    'assistant': ('processes.add_process', 'customers.add_customer', 'documents.add_document'),
    'lawyer': ('processes.change_process', 'documents.change_document', 'deadlines.change_deadline'),
    'manager': ('memberships.change_membership', 'organizations.change_organization', 'offices.change_office'),
    'admin': ('memberships.change_membership', 'offices.add_office', 'offices.change_office', 'organizations.change_organization'),
    'org_admin': ('memberships.change_membership', 'offices.add_office', 'offices.change_office', 'organizations.change_organization'),
}


def require_role(*allowed_roles):
    needed = []
    for role in allowed_roles:
        needed.extend(_ROLE_TO_PERMS.get(role, ()))
    needed = tuple(dict.fromkeys(needed))
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            m = getattr(request, 'membership', None)
            if not m:
                return _forbidden_response(request, 'Sem vínculo ativo no contexto.')
            if needed and membership_has_perm(request, *needed):
                return view_func(request, *args, **kwargs)
            if getattr(m, 'role', None) in allowed_roles:  # fallback legado temporário
                return view_func(request, *args, **kwargs)
            return _forbidden_response(request, 'Permissão insuficiente (decorator legado).')
        return wrapper
    return decorator
