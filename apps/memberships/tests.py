"""
Testes de isolamento multi-tenant para o sistema de permissões do JuridicFlow.

Roda com: python manage.py test apps.memberships.tests -v 2
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, RequestFactory

from apps.memberships.models import Membership, LocalRole, PermissionGroupProfile
from apps.organizations.models import Organization
from apps.offices.models import Office
from apps.shared.middleware import TenantContextMiddleware
from apps.shared.permissions import membership_has_perm

User = get_user_model()


def _make_user(email):
    return User.objects.create_user(email=email, password="test123", first_name="Test")


def _make_org(name):
    return Organization.objects.create(name=name, email=f"contato@{name.lower()}.com")


def _make_office(org, name):
    return Office.objects.create(organization=org, name=name, is_active=True)


def _make_group_with_perm(group_name, app_label, codename):
    group, _ = Group.objects.get_or_create(name=group_name)
    try:
        perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        group.permissions.add(perm)
    except Permission.DoesNotExist:
        pass
    return group


def _make_membership(user, org, office=None, groups=None):
    m = Membership.objects.create(user=user, organization=org, office=office, role="staff")
    if groups:
        m.groups.set(groups)
    return m


class MembershipPermissionTest(TestCase):
    """Testa que permissões são corretamente derivadas dos Groups do Membership."""

    def setUp(self):
        self.org = _make_org("OrgA")
        self.office = _make_office(self.org, "OfficeA1")
        self.user = _make_user("user@orga.com")
        self.view_group = _make_group_with_perm("PROCESS_VIEW_TEST", "auth", "view_permission")
        self.full_group = _make_group_with_perm("PROCESS_FULL_TEST", "auth", "delete_permission")

    def test_membership_has_perm_when_group_assigned(self):
        """Membro com grupo PROCESS_VIEW deve ter permissão view."""
        m = _make_membership(self.user, self.org, self.office, [self.view_group])
        perms = m.get_all_permissions()
        self.assertIn("auth.view_permission", perms)

    def test_membership_no_perm_without_group(self):
        """Membro sem grupos não deve ter nenhuma permissão."""
        m = _make_membership(self.user, self.org, self.office)
        perms = m.get_all_permissions()
        self.assertEqual(perms, set())

    def test_has_perm_method(self):
        m = _make_membership(self.user, self.org, self.office, [self.view_group])
        self.assertTrue(m.has_perm("auth.view_permission"))
        self.assertFalse(m.has_perm("auth.delete_permission"))

    def test_has_any_perm(self):
        m = _make_membership(self.user, self.org, self.office, [self.view_group])
        self.assertTrue(m.has_any_perm("auth.view_permission", "auth.delete_permission"))
        self.assertFalse(m.has_any_perm("auth.delete_permission", "auth.add_group"))

    def test_has_all_perms(self):
        m = _make_membership(self.user, self.org, self.office, [self.view_group, self.full_group])
        self.assertTrue(m.has_all_perms("auth.view_permission", "auth.delete_permission"))

    def test_sync_groups_from_local_role(self):
        """sync_groups_from_local_role deve copiar groups da LocalRole para Membership."""
        local_role = LocalRole.objects.create(name="Advogado", organization=self.org)
        local_role.groups.set([self.view_group, self.full_group])

        m = _make_membership(self.user, self.org, self.office)
        m.local_role = local_role
        m.save()
        m.sync_groups_from_local_role()

        self.assertIn(self.view_group, m.groups.all())
        self.assertIn(self.full_group, m.groups.all())


class SingleOrgRuleTest(TestCase):
    """Testa que um usuário não pode pertencer a mais de uma organização."""

    def setUp(self):
        self.org_a = _make_org("OrgA2")
        self.org_b = _make_org("OrgB2")
        self.office_a = _make_office(self.org_a, "Office-A")
        self.office_b = _make_office(self.org_b, "Office-B")
        self.user = _make_user("shared@test.com")

    def test_user_cannot_join_two_orgs(self):
        """Criar Membership em org_b quando já existe em org_a deve falhar com ValidationError."""
        from django.core.exceptions import ValidationError
        _make_membership(self.user, self.org_a, self.office_a)
        with self.assertRaises(ValidationError):
            _make_membership(self.user, self.org_b, self.office_b)


class TenantMiddlewareTest(TestCase):
    """Testa que o middleware não aceita office_id adulterado sem membership."""

    def setUp(self):
        self.factory = RequestFactory()
        self.org = _make_org("OrgMiddleware")
        self.office_legit = _make_office(self.org, "OfficeLegit")
        self.office_fake = _make_office(self.org, "OfficeFake")
        self.user = _make_user("mw@test.com")
        self.membership = _make_membership(self.user, self.org, self.office_legit)

    def _build_request(self, user, session_data=None, headers=None):
        request = self.factory.get("/")
        request.user = user
        request.session = dict(session_data or {})
        for k, v in (headers or {}).items():
            request.META[k] = v
        return request

    def test_valid_office_sets_membership(self):
        """Com office_id válido na sessão, middleware deve setar request.membership."""
        request = self._build_request(
            self.user,
            session_data={"office_id": self.office_legit.pk},
        )
        mw = TenantContextMiddleware(lambda r: None)
        mw.process_request(request)
        self.assertEqual(request.membership, self.membership)
        self.assertEqual(request.office, self.office_legit)

    def test_fake_office_id_cleared(self):
        """Com office_id de escritório sem membership, middleware deve ignorar (office=None)."""
        request = self._build_request(
            self.user,
            session_data={"office_id": self.office_fake.pk},
        )
        mw = TenantContextMiddleware(lambda r: None)
        mw.process_request(request)
        self.assertIsNone(request.office)
        self.assertNotEqual(request.membership.office_id if request.membership else None, self.office_fake.pk)

    def test_unauthenticated_user_no_context(self):
        """Usuário não autenticado não deve ter contexto de tenant."""
        from django.contrib.auth.models import AnonymousUser
        request = self._build_request(AnonymousUser())
        mw = TenantContextMiddleware(lambda r: None)
        mw.process_request(request)
        self.assertIsNone(request.organization)
        self.assertIsNone(request.membership)
        self.assertEqual(request.effective_perms, set())

    def test_effective_perms_loaded_for_active_membership(self):
        """Com membership válido, effective_perms deve ter as perms dos grupos."""
        view_group = _make_group_with_perm("MW_VIEW_TEST", "auth", "view_permission")
        self.membership.groups.set([view_group])

        request = self._build_request(
            self.user,
            session_data={"office_id": self.office_legit.pk},
        )
        mw = TenantContextMiddleware(lambda r: None)
        mw.process_request(request)
        self.assertIn("auth.view_permission", request.effective_perms)


class PermissionGroupProfileTest(TestCase):
    """Testa que grupos internos não são atribuíveis por org admins."""

    def test_internal_group_not_assignable(self):
        group = Group.objects.create(name="INTERNAL_SUPERGROUP_TEST")
        PermissionGroupProfile.objects.create(
            group=group,
            slug="internal-supergroup-test",
            is_assignable_by_org_admin=False,
            is_internal_only=True,
            sort_order=999,
        )
        assignable = Group.objects.filter(profile__is_assignable_by_org_admin=True)
        self.assertNotIn(group, assignable)
