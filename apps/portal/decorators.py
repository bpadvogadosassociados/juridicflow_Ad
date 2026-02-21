from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt


def require_portal_access(check_office=True):
    """
    Decorator para views do portal (HTML).
    
    - Exige autenticação
    - Bloqueia staff/superuser
    - Verifica membership
    - Se check_office=True, exige office selecionado (org_admin pode escolher)
    
    Uso:
        @require_portal_access()
        def minha_view(request):
            # request.office e request.organization já estão disponíveis
            ...
    
        @require_portal_access(check_office=False)
        def escolher_office(request):
            # Permite org_admin sem office
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # 1. Bloqueia staff/superuser
            if request.user.is_staff or request.user.is_superuser:
                return HttpResponseForbidden(
                    "Conta administrativa não pode acessar o portal. Use /admin"
                )
            
            # 2. Verifica membership
            membership = getattr(request, "membership", None)
            if not membership:
                return redirect("portal:login")
            
            # 3. Se não precisa verificar office, pode prosseguir
            if not check_office:
                return view_func(request, *args, **kwargs)
            
            # 4. Org admin sem office -> escolher
            if membership.role == "org_admin" and getattr(request, "office", None) is None:
                offices = list(request.organization.offices.all().order_by("name"))
                return render(request, "portal/choose_office.html", {
                    "offices": offices,
                    "active_page": ""
                })
            
            # 5. Verifica se tem office
            if getattr(request, "office", None) is None:
                return HttpResponseForbidden("Sem escritório no contexto.")
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_portal_json(check_office=True):
    """
    Decorator para endpoints JSON do portal.
    Retorna JsonResponse em vez de HTML em caso de erro.
    Aplica csrf_exempt pois esses endpoints recebem JSON body
    e o CSRF é validado via header X-CSRFToken pelo middleware.
    
    Uso:
        @require_portal_json()
        def minha_api(request):
            return JsonResponse({"data": "..."})
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # 1. Bloqueia staff/superuser
            if request.user.is_staff or request.user.is_superuser:
                return JsonResponse({"error": "forbidden"}, status=403)
            
            # 2. Verifica membership
            membership = getattr(request, "membership", None)
            if not membership:
                return JsonResponse({"error": "unauthorized"}, status=401)
            
            # 3. Se não precisa verificar office, pode prosseguir
            if not check_office:
                return view_func(request, *args, **kwargs)
            
            # 4. Verifica se tem office
            if getattr(request, "office", None) is None:
                return JsonResponse({"error": "office_required"}, status=400)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator