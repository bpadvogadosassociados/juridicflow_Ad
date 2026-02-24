
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render


def _office_choices_from_memberships(request):
    offices = {}
    for m in (getattr(request, 'available_memberships', []) or []):
        if m.office_id and m.office and getattr(m.office, 'is_active', True):
            offices[m.office_id] = m.office
    return sorted(offices.values(), key=lambda o: o.name.lower())


def require_portal_access(check_office=True):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_staff or request.user.is_superuser:
                return HttpResponseForbidden('Conta administrativa não pode acessar o portal. Use /admin')
            if not getattr(request, 'organization', None):
                return HttpResponseForbidden('Sem organização vinculada.')
            if not getattr(request, 'membership', None):
                return HttpResponseForbidden('Sem vínculo ativo.')
            if not check_office:
                return view_func(request, *args, **kwargs)
            if getattr(request, 'office', None) is None:
                offices = _office_choices_from_memberships(request)
                if offices:
                    return render(request, 'portal/choose_office.html', {'offices': offices, 'active_page': ''})
                return HttpResponseForbidden('Sem escritório no contexto.')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_portal_json(check_office=True):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_staff or request.user.is_superuser:
                return JsonResponse({'error': 'forbidden'}, status=403)
            if not getattr(request, 'organization', None):
                return JsonResponse({'error': 'organization_required'}, status=403)
            if not getattr(request, 'membership', None):
                return JsonResponse({'error': 'membership_required'}, status=403)
            if check_office and getattr(request, 'office', None) is None:
                return JsonResponse({'error': 'office_required'}, status=400)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
