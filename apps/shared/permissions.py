"""
Sistema de permissões granulares para o portal.

Hierarquia de roles (do mais alto ao mais baixo):
    org_admin  → Acesso total na organização
    admin      → Acesso total no office
    manager    → Gerencia equipe, vê relatórios, edita tudo
    lawyer     → CRUD processos, prazos, documentos, contatos
    assistant  → CRUD limitado (sem deletar, sem financeiro)
    intern     → Somente leitura + criar interações

Uso nas views:
    from apps.portal.permissions import require_role

    @require_portal_access()
    @require_role("lawyer")
    def processo_create(request):
        ...

    @require_portal_json()
    @require_role("manager", "admin")
    def financeiro_despesa_delete(request, expense_id):
        ...
"""
from functools import wraps

from django.http import HttpResponseForbidden, JsonResponse


# ==================== ROLE HIERARCHY ====================

ROLE_HIERARCHY = {
    "org_admin": 100,
    "admin": 90,
    "manager": 70,
    "lawyer": 50,
    "assistant": 30,
    "intern": 10,
}

# Nível mínimo para cada tipo de ação
ACTION_MIN_LEVELS = {
    # Financeiro
    "finance_view": 50,        # lawyer+
    "finance_create": 70,      # manager+
    "finance_edit": 70,        # manager+
    "finance_delete": 90,      # admin+

    # Processos
    "process_view": 10,        # todos
    "process_create": 50,      # lawyer+
    "process_edit": 50,        # lawyer+
    "process_delete": 70,      # manager+

    # Contatos
    "customer_view": 10,       # todos
    "customer_create": 30,     # assistant+
    "customer_edit": 50,       # lawyer+
    "customer_delete": 70,     # manager+
    "customer_export": 50,     # lawyer+
    "customer_import": 70,     # manager+

    # Documentos
    "document_view": 10,       # todos
    "document_upload": 30,     # assistant+
    "document_edit": 50,       # lawyer+
    "document_delete": 70,     # manager+

    # Prazos
    "deadline_view": 10,       # todos
    "deadline_create": 50,     # lawyer+
    "deadline_edit": 50,       # lawyer+
    "deadline_delete": 70,     # manager+

    # Tarefas
    "task_view": 10,           # todos
    "task_create": 30,         # assistant+
    "task_edit": 30,           # assistant+
    "task_delete": 70,         # manager+

    # Publicações
    "publication_view": 10,    # todos
    "publication_import": 50,  # lawyer+
    "publication_manage": 70,  # manager+

    # Configurações
    "settings_view": 70,       # manager+
    "settings_edit": 90,       # admin+

    # Equipe
    "team_view": 70,           # manager+
    "team_manage": 90,         # admin+
}


def get_role_level(role: str) -> int:
    """Retorna o nível numérico de uma role."""
    return ROLE_HIERARCHY.get(role, 0)


def has_min_role(user_role: str, min_role: str) -> bool:
    """Verifica se user_role tem nível >= min_role."""
    return get_role_level(user_role) >= get_role_level(min_role)


def can_perform(user_role: str, action: str) -> bool:
    """Verifica se a role pode executar a ação."""
    min_level = ACTION_MIN_LEVELS.get(action, 100)  # default: só org_admin
    return get_role_level(user_role) >= min_level


# ==================== DECORATORS ====================

def require_role(*allowed_roles):
    """
    Decorator que verifica se o membership do usuário tem uma das roles permitidas
    OU uma role de nível superior.

    Deve ser usado DEPOIS de @require_portal_access() ou @require_portal_json(),
    pois depende de request.membership existir.

    Exemplos:
        @require_role("lawyer")           → lawyer, manager, admin, org_admin
        @require_role("manager", "admin") → manager, admin, org_admin

    Para org_admin, SEMPRE passa (nível máximo).
    """
    # Calcula o nível mínimo entre as roles permitidas
    min_level = min(get_role_level(r) for r in allowed_roles) if allowed_roles else 100

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            membership = getattr(request, "membership", None)
            if not membership:
                return _forbidden_response(request, "Sem membership no contexto.")

            user_level = get_role_level(membership.role)
            if user_level < min_level:
                return _forbidden_response(
                    request,
                    f"Permissão insuficiente. Necessário: {', '.join(allowed_roles)} ou superior."
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_action(action: str):
    """
    Decorator que verifica permissão por ação granular.

    Exemplos:
        @require_action("finance_delete")  → admin+ (nível 90)
        @require_action("task_create")     → assistant+ (nível 30)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            membership = getattr(request, "membership", None)
            if not membership:
                return _forbidden_response(request, "Sem membership no contexto.")

            if not can_perform(membership.role, action):
                return _forbidden_response(
                    request,
                    f"Sem permissão para '{action}'."
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def _forbidden_response(request, message: str):
    """Retorna 403 no formato correto (HTML ou JSON)."""
    # Heurística: se Accept contém json ou se é XHR, retorna JSON
    accept = request.META.get("HTTP_ACCEPT", "")
    is_xhr = request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"

    if "application/json" in accept or is_xhr:
        return JsonResponse({"error": "forbidden", "detail": message}, status=403)
    return HttpResponseForbidden(message)


# ==================== TEMPLATE HELPERS ====================

def get_user_permissions(role: str) -> dict[str, bool]:
    """
    Retorna dict com todas as permissões para uma role.
    Útil para passar ao template context e controlar visibilidade de botões.

    Uso na view:
        context["perms"] = get_user_permissions(request.membership.role)

    Uso no template:
        {% if perms.finance_delete %}
            <button>Excluir</button>
        {% endif %}
    """
    level = get_role_level(role)
    return {action: level >= min_level for action, min_level in ACTION_MIN_LEVELS.items()}


# ==================== CONTEXT PROCESSOR ====================

def portal_permissions(request):
    """
    Context processor que injeta permissões no template.

    Adicione em settings.py → TEMPLATES → OPTIONS → context_processors:
        "apps.portal.permissions.portal_permissions"
    """
    membership = getattr(request, "membership", None)
    if not membership:
        return {"user_role": None, "portal_perms": {}}

    return {
        "user_role": membership.role,
        "user_role_display": dict(
            org_admin="Administrador Org",
            admin="Administrador",
            manager="Gerente",
            lawyer="Advogado",
            assistant="Assistente",
            intern="Estagiário",
        ).get(membership.role, membership.role),
        "portal_perms": get_user_permissions(membership.role),
    }