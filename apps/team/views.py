"""
Team Management API — gerenciamento de membros do escritório.

GET    /api/team/members/              — lista membros do escritório ativo
POST   /api/team/members/              — adicionar membro (por email)
PATCH  /api/team/members/<id>/         — editar role/local_role
DELETE /api/team/members/<id>/         — remover membro

GET    /api/team/local-roles/          — listar funções locais do escritório
POST   /api/team/local-roles/          — criar função local
PATCH  /api/team/local-roles/<id>/     — editar função local
DELETE /api/team/local-roles/<id>/     — excluir função local

GET    /api/team/groups/               — listar grupos assignáveis ao office admin
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as drf_serializers

from apps.api.permissions import IsInTenant
from apps.memberships.models import Membership, LocalRole, PermissionGroupProfile
from apps.activity.models import log_event

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de permissão
# ─────────────────────────────────────────────────────────────────────────────

def _can_manage_team(request):
    """
    Retorna True se o usuário tem permissão de gerenciar equipe.
    Verifica: role org_admin / office_admin OU permissão granular.
    """
    membership = getattr(request, "membership", None)
    if not membership:
        return False
    if membership.role in ("org_admin", "office_admin"):
        return True
    return membership.has_any_perm(
        "memberships.add_membership",
        "memberships.change_membership",
        "memberships.delete_membership",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Serializers inline (simples, neste arquivo para facilitar manutenção)
# ─────────────────────────────────────────────────────────────────────────────

class MemberSerializer(drf_serializers.ModelSerializer):
    user_id     = drf_serializers.IntegerField(source="user.id", read_only=True)
    full_name   = drf_serializers.SerializerMethodField()
    email       = drf_serializers.EmailField(source="user.email", read_only=True)
    local_role_name = drf_serializers.SerializerMethodField()
    groups_ids  = drf_serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            "id", "user_id", "full_name", "email",
            "role", "local_role", "local_role_name",
            "groups_ids", "is_active", "created_at",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_local_role_name(self, obj):
        return obj.local_role.name if obj.local_role_id else None

    def get_groups_ids(self, obj):
        return list(obj.groups.values_list("id", flat=True))


class LocalRoleSerializer(drf_serializers.ModelSerializer):
    groups_ids = drf_serializers.SerializerMethodField()

    class Meta:
        model = LocalRole
        fields = ["id", "name", "description", "groups_ids", "is_active"]

    def get_groups_ids(self, obj):
        return list(obj.groups.values_list("id", flat=True))


class GroupSerializer(drf_serializers.ModelSerializer):
    description = drf_serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "description"]

    def get_description(self, obj):
        try:
            return obj.profile.description
        except Exception:
            return ""


# ─────────────────────────────────────────────────────────────────────────────
# Views
# ─────────────────────────────────────────────────────────────────────────────

class TeamMembersView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        if not getattr(request, "office", None):
            return Response({"detail": "X-Office-Id obrigatório."}, status=400)

        qs = (
            Membership.objects.filter(
                organization=request.organization,
                office=request.office,
                is_active=True,
            )
            .select_related("user", "local_role")
            .prefetch_related("groups")
            .order_by("user__first_name", "user__email")
        )
        return Response(MemberSerializer(qs, many=True).data)

    def post(self, request):
        """Adicionar membro por e-mail."""
        if not _can_manage_team(request):
            return Response({"detail": "Permissão insuficiente."}, status=403)

        email = (request.data.get("email") or "").strip()
        role  = request.data.get("role", "staff")
        local_role_id = request.data.get("local_role")

        if not email:
            return Response({"detail": "Campo 'email' obrigatório."}, status=400)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({"detail": f"Usuário com e-mail '{email}' não encontrado."}, status=404)

        if Membership.objects.filter(
            user=user,
            organization=request.organization,
            office=request.office,
        ).exists():
            return Response({"detail": "Usuário já é membro deste escritório."}, status=400)

        local_role = None
        if local_role_id:
            try:
                local_role = LocalRole.objects.get(
                    id=local_role_id,
                    organization=request.organization,
                )
            except LocalRole.DoesNotExist:
                return Response({"detail": "Função local não encontrada."}, status=404)

        membership = Membership.objects.create(
            user=user,
            organization=request.organization,
            office=request.office,
            role=role,
            local_role=local_role,
        )
        if local_role:
            membership.sync_groups_from_local_role()

        log_event(
            module="team",
            action="member_added",
            summary=f"{request.user.get_full_name() or request.user.email} adicionou {user.get_full_name() or user.email} ao escritório",
            actor=request.user,
            organization=request.organization,
            office=request.office,
            entity_type="Membership",
            entity_id=str(membership.id),
            entity_label=user.get_full_name() or user.email,
            request=request,
        )
        return Response(MemberSerializer(membership).data, status=201)


class TeamMemberDetailView(APIView):
    permission_classes = [IsInTenant]

    def _get_membership(self, request, pk):
        try:
            return Membership.objects.get(
                id=pk,
                organization=request.organization,
                office=request.office,
            )
        except Membership.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not _can_manage_team(request):
            return Response({"detail": "Permissão insuficiente."}, status=403)

        membership = self._get_membership(request, pk)
        if not membership:
            return Response({"detail": "Membro não encontrado."}, status=404)

        if "role" in request.data:
            membership.role = request.data["role"]

        if "local_role" in request.data:
            lr_id = request.data["local_role"]
            if lr_id:
                try:
                    lr = LocalRole.objects.get(id=lr_id, organization=request.organization)
                    membership.local_role = lr
                except LocalRole.DoesNotExist:
                    return Response({"detail": "Função local não encontrada."}, status=404)
            else:
                membership.local_role = None

        if "groups" in request.data:
            group_ids = request.data["groups"] or []
            assignable = _assignable_group_ids(request)
            invalid = set(group_ids) - set(assignable)
            if invalid:
                return Response({"detail": "Grupos não assignáveis."}, status=400)
            membership.groups.set(group_ids)

        membership.save()

        if membership.local_role_id and "local_role" in request.data:
            membership.sync_groups_from_local_role()

        log_event(
            module="team",
            action="role_changed",
            summary=f"{request.user.get_full_name() or request.user.email} alterou função de {membership.user.get_full_name() or membership.user.email}",
            actor=request.user,
            organization=request.organization,
            office=request.office,
            entity_type="Membership",
            entity_id=str(membership.id),
            entity_label=membership.user.get_full_name() or membership.user.email,
            request=request,
        )
        return Response(MemberSerializer(membership).data)

    def delete(self, request, pk):
        if not _can_manage_team(request):
            return Response({"detail": "Permissão insuficiente."}, status=403)

        membership = self._get_membership(request, pk)
        if not membership:
            return Response({"detail": "Membro não encontrado."}, status=404)

        if membership.user_id == request.user.id:
            return Response({"detail": "Você não pode remover a si mesmo."}, status=400)

        name = membership.user.get_full_name() or membership.user.email
        membership.delete()

        log_event(
            module="team",
            action="member_removed",
            summary=f"{request.user.get_full_name() or request.user.email} removeu {name} do escritório",
            actor=request.user,
            organization=request.organization,
            office=request.office,
            entity_type="Membership",
            entity_id=str(pk),
            entity_label=name,
            request=request,
        )
        return Response(status=204)


# ─────────────────────────────────────────────────────────────────────────────
# Local Roles
# ─────────────────────────────────────────────────────────────────────────────

class LocalRoleListView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        from django.db.models import Q
        qs = LocalRole.objects.filter(
            organization=request.organization,
            is_active=True,
        ).filter(
            # roles do office atual OU roles globais da org (office=None)
            Q(office=request.office) | Q(office__isnull=True),
        ).prefetch_related("groups").order_by("name")
        return Response(LocalRoleSerializer(qs, many=True).data)

    def post(self, request):
        if not _can_manage_team(request):
            return Response({"detail": "Permissão insuficiente."}, status=403)

        name        = (request.data.get("name") or "").strip()
        description = request.data.get("description", "")
        group_ids   = request.data.get("groups", [])

        if not name:
            return Response({"detail": "Campo 'name' obrigatório."}, status=400)

        if LocalRole.objects.filter(
            organization=request.organization,
            office=request.office,
            name=name,
        ).exists():
            return Response({"detail": "Já existe uma função com este nome."}, status=400)

        role = LocalRole.objects.create(
            organization=request.organization,
            office=request.office,
            name=name,
            description=description,
        )
        if group_ids:
            assignable = _assignable_group_ids(request)
            role.groups.set([g for g in group_ids if g in assignable])

        log_event(
            module="team",
            action="created",
            summary=f"{request.user.get_full_name() or request.user.email} criou função '{name}'",
            actor=request.user,
            organization=request.organization,
            office=request.office,
            entity_type="LocalRole",
            entity_id=str(role.id),
            entity_label=name,
            request=request,
        )
        return Response(LocalRoleSerializer(role).data, status=201)


class LocalRoleDetailView(APIView):
    permission_classes = [IsInTenant]

    def _get(self, request, pk):
        try:
            return LocalRole.objects.get(
                id=pk,
                organization=request.organization,
            )
        except LocalRole.DoesNotExist:
            return None

    def patch(self, request, pk):
        if not _can_manage_team(request):
            return Response({"detail": "Permissão insuficiente."}, status=403)
        role = self._get(request, pk)
        if not role:
            return Response({"detail": "Função não encontrada."}, status=404)

        if "name" in request.data:
            role.name = request.data["name"]
        if "description" in request.data:
            role.description = request.data["description"]
        if "groups" in request.data:
            assignable = _assignable_group_ids(request)
            role.groups.set([g for g in request.data["groups"] if g in assignable])
        role.save()
        return Response(LocalRoleSerializer(role).data)

    def delete(self, request, pk):
        if not _can_manage_team(request):
            return Response({"detail": "Permissão insuficiente."}, status=403)
        role = self._get(request, pk)
        if not role:
            return Response({"detail": "Função não encontrada."}, status=404)
        role.is_active = False
        role.save(update_fields=["is_active"])
        return Response(status=204)


# ─────────────────────────────────────────────────────────────────────────────
# Permission Groups
# ─────────────────────────────────────────────────────────────────────────────

def _assignable_group_ids(request):
    """IDs dos grupos assignáveis pelo office admin."""
    profiles = PermissionGroupProfile.objects.filter(
        is_assignable_by_org_admin=True,
        is_internal_only=False,
    ).values_list("group_id", flat=True)
    return set(profiles)


class PermissionGroupsView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        """Lista grupos assignáveis pelo org admin."""
        profile_qs = PermissionGroupProfile.objects.filter(
            is_assignable_by_org_admin=True,
            is_internal_only=False,
        ).select_related("group").order_by("sort_order", "group__name")

        data = []
        for p in profile_qs:
            data.append({
                "id":          p.group.id,
                "name":        p.group.name,
                "description": p.description,
            })

        # Fallback: se não há profiles cadastrados, retorna todos os grupos
        if not data:
            groups = Group.objects.all().order_by("name")
            data = [{"id": g.id, "name": g.name, "description": ""} for g in groups]

        return Response(data)
