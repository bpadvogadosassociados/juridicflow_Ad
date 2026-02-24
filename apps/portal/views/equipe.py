"""
Views de Gestão de Equipe — Aba Equipe no portal.

Permite que Org Admins e Diretores Técnicos:
  - Listar membros do office ativo
  - Criar LocalRoles (funções) combinando grupos globais assignáveis
  - Convidar/adicionar usuários com uma função
  - Editar/remover membros

Segurança:
  - Todas as rotas exigem `memberships.view_membership` para leitura
  - Rotas de escrita exigem `memberships.add_membership` / `memberships.change_membership`
  - LocalRole só pode usar groups com is_assignable_by_org_admin=True (filtrado na UI)
  - Ninguém pode atribuir o grupo ORG_ADMIN_FULL (is_internal_only=True) por aqui
"""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.memberships.models import Membership, LocalRole, PermissionGroupProfile
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.views._helpers import log_activity, parse_json_body
from apps.shared.permissions import require_membership_perm

User = get_user_model()


def _assignable_groups(request):
    """Retorna Groups que Org Admins podem usar em LocalRoles (não internos)."""
    internal_slugs = PermissionGroupProfile.objects.filter(
        is_internal_only=True
    ).values_list("group_id", flat=True)
    return (
        Group.objects.filter(profile__is_assignable_by_org_admin=True)
        .exclude(id__in=internal_slugs)
        .order_by("profile__sort_order", "name")
    )


# ──────────────────────────────────────────────────────────────────────────────
# Lista de membros
# ──────────────────────────────────────────────────────────────────────────────

@require_portal_access()
@require_membership_perm("memberships.view_membership")
def equipe(request):
    """Lista membros do office ativo."""
    office = request.office
    org = request.organization

    members = (
        Membership.objects.filter(organization=org, office=office, is_active=True)
        .select_related("user", "local_role")
        .prefetch_related("groups")
        .order_by("user__first_name", "user__email")
    )

    from django.db.models import Q
    local_roles = (
        LocalRole.objects.filter(organization=org, is_active=True)
        .filter(Q(office=office) | Q(office__isnull=True))
        .order_by("name")
    )

    return render(request, "portal/equipe/lista.html", {
        "active_page": "equipe",
        "members": members,
        "local_roles": local_roles,
        "office": office,
    })


# ──────────────────────────────────────────────────────────────────────────────
# Adicionar membro
# ──────────────────────────────────────────────────────────────────────────────

@require_portal_access()
@require_membership_perm("memberships.add_membership")
@require_http_methods(["GET", "POST"])
def equipe_membro_add(request):
    """Adiciona um usuário existente ao office ativo com uma função local."""
    office = request.office
    org = request.organization

    local_roles = LocalRole.objects.filter(
        organization=org, is_active=True
    ).order_by("name")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        local_role_id = request.POST.get("local_role_id")
        role_label = request.POST.get("role_label", "staff")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, f"Usuário com e-mail '{email}' não encontrado.")
            return redirect("portal:equipe")

        # Regra: usuário já pertence a outra org?
        other_org = (
            Membership.objects.filter(user=user)
            .exclude(organization=org)
            .exists()
        )
        if other_org:
            messages.error(request, "Este usuário já pertence a outra organização e não pode ser adicionado aqui.")
            return redirect("portal:equipe")

        # Já tem membership neste office?
        existing = Membership.objects.filter(user=user, organization=org, office=office).first()
        if existing:
            messages.warning(request, "Usuário já é membro deste escritório.")
            return redirect("portal:equipe")

        local_role = None
        if local_role_id:
            try:
                local_role = LocalRole.objects.get(pk=local_role_id, organization=org)
            except LocalRole.DoesNotExist:
                messages.error(request, "Função local inválida.")
                return redirect("portal:equipe")

        membership = Membership(
            user=user,
            organization=org,
            office=office,
            role=role_label,
            local_role=local_role,
            is_active=True,
        )
        membership.save()

        if local_role:
            membership.sync_groups_from_local_role()

        log_activity(request, f"Membro adicionado: {user.email} → {office.name} ({local_role})")
        messages.success(request, f"{user.email} adicionado ao escritório com sucesso.")
        return redirect("portal:equipe")

    return render(request, "portal/equipe/add_membro.html", {
        "active_page": "equipe",
        "local_roles": local_roles,
        "office": office,
    })


# ──────────────────────────────────────────────────────────────────────────────
# Editar membro (trocar função)
# ──────────────────────────────────────────────────────────────────────────────

@require_portal_json()
@require_membership_perm("memberships.change_membership")
@require_http_methods(["POST"])
def equipe_membro_update(request, membership_id):
    """Troca a função (LocalRole) de um membro. Resync automático dos groups."""
    office = request.office
    org = request.organization

    membership = get_object_or_404(Membership, pk=membership_id, organization=org, office=office)
    data = parse_json_body(request)
    local_role_id = data.get("local_role_id")

    if local_role_id:
        local_role = get_object_or_404(LocalRole, pk=local_role_id, organization=org)
        membership.local_role = local_role
    else:
        membership.local_role = None

    membership.save(update_fields=["local_role"])
    membership.sync_groups_from_local_role()

    return JsonResponse({
        "ok": True,
        "membership_id": membership.pk,
        "local_role": str(membership.local_role) if membership.local_role else None,
    })


# ──────────────────────────────────────────────────────────────────────────────
# Remover membro
# ──────────────────────────────────────────────────────────────────────────────

@require_portal_json()
@require_membership_perm("memberships.delete_membership")
@require_http_methods(["POST"])
def equipe_membro_remove(request, membership_id):
    """Remove (desativa) um membro do office."""
    office = request.office
    org = request.organization

    membership = get_object_or_404(Membership, pk=membership_id, organization=org, office=office)

    # Proteção: não remover a si mesmo
    if membership.user_id == request.user.pk:
        return JsonResponse({"error": "Você não pode remover seu próprio vínculo."}, status=400)

    membership.is_active = False
    membership.save(update_fields=["is_active"])
    membership.groups.clear()

    log_activity(request, f"Membro removido: {membership.user.email} de {office.name}")
    return JsonResponse({"ok": True, "membership_id": membership_id})


# ──────────────────────────────────────────────────────────────────────────────
# LocalRoles (Funções Locais)
# ──────────────────────────────────────────────────────────────────────────────

@require_portal_access()
@require_membership_perm("memberships.view_localrole")
def equipe_funcoes(request):
    """Lista funções locais da organização."""
    org = request.organization
    office = request.office

    funcoes = (
        LocalRole.objects.filter(organization=org)
        .prefetch_related("groups")
        .order_by("name")
    )

    assignable = list(_assignable_groups(request))

    return render(request, "portal/equipe/funcoes.html", {
        "active_page": "equipe",
        "funcoes": funcoes,
        "assignable_groups": assignable,
        "office": office,
    })


@require_portal_json()
@require_membership_perm("memberships.add_localrole")
@require_http_methods(["POST"])
def equipe_funcao_create(request):
    """Cria uma função local. Só permite grupos assignable_by_org_admin=True."""
    org = request.organization
    data = parse_json_body(request)

    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    office_id = data.get("office_id")
    group_ids = data.get("group_ids") or []

    if not name:
        return JsonResponse({"error": "Nome da função é obrigatório."}, status=400)

    # Valida grupos (apenas assignable)
    allowed_ids = set(
        PermissionGroupProfile.objects.filter(is_assignable_by_org_admin=True, is_internal_only=False)
        .values_list("group_id", flat=True)
    )
    group_ids_clean = [gid for gid in group_ids if gid in allowed_ids]
    groups = Group.objects.filter(id__in=group_ids_clean)

    office = None
    if office_id:
        from apps.offices.models import Office
        office = get_object_or_404(Office, pk=office_id, organization=org)

    if LocalRole.objects.filter(organization=org, office=office, name=name).exists():
        return JsonResponse({"error": f"Já existe uma função com o nome '{name}' neste escopo."}, status=400)

    local_role = LocalRole.objects.create(
        organization=org,
        office=office,
        name=name,
        description=description,
    )
    local_role.groups.set(groups)

    return JsonResponse({
        "ok": True,
        "id": local_role.pk,
        "name": local_role.name,
        "group_count": groups.count(),
    }, status=201)


@require_portal_json()
@require_membership_perm("memberships.change_localrole")
@require_http_methods(["POST"])
def equipe_funcao_update(request, role_id):
    """Atualiza uma função local e re-sincroniza todos os memberships que usam ela."""
    org = request.organization
    local_role = get_object_or_404(LocalRole, pk=role_id, organization=org)
    data = parse_json_body(request)

    name = (data.get("name") or local_role.name).strip()
    description = (data.get("description") or local_role.description).strip()
    group_ids = data.get("group_ids")

    if name != local_role.name and LocalRole.objects.filter(
        organization=org, office=local_role.office, name=name
    ).exclude(pk=role_id).exists():
        return JsonResponse({"error": f"Já existe uma função com o nome '{name}'."}, status=400)

    local_role.name = name
    local_role.description = description
    local_role.save(update_fields=["name", "description"])

    if group_ids is not None:
        allowed_ids = set(
            PermissionGroupProfile.objects.filter(is_assignable_by_org_admin=True, is_internal_only=False)
            .values_list("group_id", flat=True)
        )
        group_ids_clean = [gid for gid in group_ids if gid in allowed_ids]
        local_role.groups.set(Group.objects.filter(id__in=group_ids_clean))

        # Re-sincroniza todos os memberships que usam esta função
        for m in Membership.objects.filter(local_role=local_role, is_active=True):
            m.sync_groups_from_local_role()

    return JsonResponse({"ok": True, "id": local_role.pk, "name": local_role.name})


@require_portal_json()
@require_membership_perm("memberships.delete_localrole")
@require_http_methods(["POST"])
def equipe_funcao_delete(request, role_id):
    """Remove uma função local. Memberships perdem a função (groups mantidos até próxima edição)."""
    org = request.organization
    local_role = get_object_or_404(LocalRole, pk=role_id, organization=org)

    # Desvincula memberships
    Membership.objects.filter(local_role=local_role).update(local_role=None)

    local_role.delete()
    return JsonResponse({"ok": True})