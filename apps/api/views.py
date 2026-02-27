"""
JuridicFlow API Views — versão completa para React frontend.

Todas as views herdam de ScopedModelViewSet que garante:
  - Autenticação JWT (IsAuthenticated via DEFAULT_PERMISSION_CLASSES)
  - Isolamento por organização + escritório (IsInTenant)
  - Permissões granulares via membership (HasMembershipViewPerms)
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Sum, OuterRef, Subquery, Count, Value, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction


from apps.memberships.models import Membership
from apps.offices.models import Office
from apps.customers.models import Customer, CustomerInteraction, CustomerRelationship
from apps.processes.models import Process, ProcessNote
from apps.deadlines.models import Deadline
from apps.documents.models import Document
from apps.finance.models import FeeAgreement, Invoice, Payment, Expense, Proposal
from apps.portal.models import (
    KanbanBoard, KanbanColumn, KanbanCard,
    CalendarEntry, CalendarEventTemplate,
    Notification, Task, 
)
from apps.activity.models import ActivityEvent
from apps.memberships.models import Invitation

from .serializers import (
    MeSerializer, MembershipSerializer, OfficeSerializer,
    CustomerSerializer, CustomerInteractionSerializer, CustomerRelationshipSerializer,
    ProcessSerializer, ProcessNoteSerializer,
    DeadlineSerializer, DocumentSerializer,
    FeeAgreementSerializer, InvoiceSerializer, PaymentSerializer,
    ExpenseSerializer, ProposalSerializer,
    KanbanBoardSerializer, KanbanColumnSerializer, KanbanCardSerializer,
    CalendarEntrySerializer, CalendarTemplateSerializer,
    TaskSerializer, NotificationSerializer, InvitationAcceptSerializer,
    InvitationCreateSerializer, InvitationPublicSerializer
)
from .permissions import IsInTenant, HasMembershipViewPerms


def _ip(request):
    return (
        request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
    )


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────

class LoginView(APIView):
    permission_classes = [AllowAny]
    # Simple in-memory rate limiting per IP
    _attempts = {}  # ip -> (count, first_attempt_time)
    MAX_ATTEMPTS = 10
    WINDOW_SECONDS = 300  # 5 minutes

    def _check_rate_limit(self, request):
        import time
        ip = _ip(request)
        now = time.time()
        attempts_info = self._attempts.get(ip)
        if attempts_info:
            count, first_time = attempts_info
            if now - first_time > self.WINDOW_SECONDS:
                self._attempts[ip] = (1, now)
                return True
            if count >= self.MAX_ATTEMPTS:
                return False
            self._attempts[ip] = (count + 1, first_time)
        else:
            self._attempts[ip] = (1, now)
        return True

    def _reset_rate_limit(self, request):
        ip = _ip(request)
        self._attempts.pop(ip, None)

    def post(self, request):
        if not self._check_rate_limit(request):
            return Response(
                {"detail": "Muitas tentativas de login. Tente novamente em alguns minutos."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            return Response(
                {"detail": "Email e senha são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {"detail": "Credenciais inválidas."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        self._reset_rate_limit(request)
        refresh = RefreshToken.for_user(user)
        from apps.activity.models import log_event
        log_event(
            module="auth",
            action="login",
            summary=f"{user.get_full_name() or user.email} fez login",
            actor=user,
            organization=None,
            office=None,
            entity_type="User",
            entity_id=str(user.id),
            entity_label=user.email,
            request=request,
            changes={"legacy_source": "shared.AuditLog"}
        )
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class MeView(APIView):
    """Dados do usuário logado. Não requer X-Office-Id."""

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class PasswordChangeView(APIView):
    """Permite ao usuário logado alterar sua senha."""

    def post(self, request):
        current = request.data.get("current_password", "")
        new_password = request.data.get("new_password", "")
        confirm = request.data.get("confirm_password", "")

        if not current or not new_password:
            return Response(
                {"detail": "Senha atual e nova senha são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if new_password != confirm:
            return Response(
                {"detail": "Nova senha e confirmação não coincidem."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_password) < 8:
            return Response(
                {"detail": "Nova senha deve ter no mínimo 8 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(current):
            return Response(
                {"detail": "Senha atual incorreta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(new_password)
        request.user.save()
        return Response({"detail": "Senha alterada com sucesso."})


class MembershipsView(APIView):
    """Lista todas as memberships ativas do usuário. Não requer X-Office-Id."""

    def get(self, request):
        qs = (
            Membership.objects.filter(user=request.user, is_active=True)
            .select_related("organization", "office")
        )
        return Response(MembershipSerializer(qs, many=True).data)


class PermissionsView(APIView):
    """
    Retorna as permissões efetivas do usuário no escritório selecionado.
    O React usa para mostrar/esconder menus e botões sem depender de roles.
    """

    def get(self, request):
        perms = sorted(getattr(request, "effective_perms", set()) or set())
        return Response({"permissions": perms})


class OfficesView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        offices = Office.objects.filter(
            memberships__user=request.user,
            memberships__organization=request.organization,
            memberships__is_active=True,
            is_active=True,
        ).distinct()
        return Response(OfficeSerializer(offices, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# Base ViewSet (scoped por org + office)
# ─────────────────────────────────────────────────────────────────────────────

class ScopedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInTenant, HasMembershipViewPerms]

    def get_queryset(self):
        qs = super().get_queryset().filter(organization=self.request.organization)
        if getattr(self.request, "office", None):
            return qs.filter(office=self.request.office)
        return qs.none()

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        if not getattr(self.request, "office", None):
            raise ValidationError(
                {"detail": "Office não selecionado. Envie header X-Office-Id."}
            )
        serializer.save(
            organization=self.request.organization,
            office=self.request.office,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Customers
# ─────────────────────────────────────────────────────────────────────────────

class CustomerViewSet(ScopedModelViewSet):
    queryset = Customer.objects.filter(is_deleted=False)
    serializer_class = CustomerSerializer
    required_perms_map = {
        "list":         ("customers.view_customer",),
        "retrieve":     ("customers.view_customer",),
        "create":       ("customers.add_customer",),
        "update":       ("customers.change_customer",),
        "partial_update": ("customers.change_customer",),
        "destroy":      ("customers.delete_customer",),
    }

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete for customers."""
        instance.soft_delete()

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(document__icontains=search) |
                Q(phone__icontains=search)
            )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        type_filter = self.request.query_params.get("type")
        if type_filter:
            qs = qs.filter(type=type_filter)
        pipeline = self.request.query_params.get("pipeline_stage")
        if pipeline:
            qs = qs.filter(pipeline_stage=pipeline)
        return qs.select_related("responsible")

    @action(detail=True, methods=["get", "post"], url_path="interactions")
    def interactions(self, request, pk=None):
        customer = self.get_object()
        if request.method == "GET":
            qs = CustomerInteraction.objects.filter(
                customer=customer,
                organization=request.organization,
                office=request.office,
            ).order_by("-date")
            serializer = CustomerInteractionSerializer(
                qs, many=True, context={"request": request}
            )
            return Response(serializer.data)
        else:
            serializer = CustomerInteractionSerializer(
                data=request.data, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(
                customer=customer,
                organization=request.organization,
                office=request.office,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="relationships")
    def relationships(self, request, pk=None):
        customer = self.get_object()
        if request.method == "GET":
            qs = CustomerRelationship.objects.filter(from_customer=customer)
            serializer = CustomerRelationshipSerializer(qs, many=True)
            return Response(serializer.data)
        else:
            serializer = CustomerRelationshipSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(from_customer=customer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# Processes
# ─────────────────────────────────────────────────────────────────────────────

class ProcessViewSet(ScopedModelViewSet):
    queryset = Process.objects.all()
    serializer_class = ProcessSerializer
    required_perms_map = {
        "list":           ("processes.view_process",),
        "retrieve":       ("processes.view_process",),
        "create":         ("processes.add_process",),
        "update":         ("processes.change_process",),
        "partial_update": ("processes.change_process",),
        "destroy":        ("processes.delete_process",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(number__icontains=search) | Q(subject__icontains=search)
            )
        if status_val := self.request.query_params.get("status"):
            qs = qs.filter(status=status_val)
        if phase := self.request.query_params.get("phase"):
            qs = qs.filter(phase=phase)
        if area := self.request.query_params.get("area"):
            qs = qs.filter(area=area)
        
        ct_id = ContentType.objects.get_for_model(Process).id
        today = timezone.now().date()

        deadlines_base = Deadline.objects.filter(
            content_type_id=ct_id,
            object_id=OuterRef("pk"),
        )

        deadlines_count_sq = (
            deadlines_base
            .values("object_id")
            .annotate(c=Count("*"))
            .values("c")[:1]
        )

        next_deadline_base = (
            deadlines_base
            .filter(status="pending", due_date__gte=today)
            .order_by("due_date")
        )

        qs = qs.annotate(
            deadlines_count=Coalesce(
                Subquery(deadlines_count_sq, output_field=IntegerField()),
                Value(0),
            ),
            next_deadline_id=Subquery(next_deadline_base.values("id")[:1]),
            next_deadline_title=Subquery(next_deadline_base.values("title")[:1]),
            next_deadline_due_date=Subquery(next_deadline_base.values("due_date")[:1]),
            next_deadline_priority=Subquery(next_deadline_base.values("priority")[:1]),
    )
        
        return qs.select_related("responsible").prefetch_related("parties")

    @action(detail=True, methods=["get", "post"], url_path="notes")
    def notes(self, request, pk=None):
        process = self.get_object()
        if request.method == "GET":
            qs = process.notes.select_related("author")
            serializer = ProcessNoteSerializer(
                qs, many=True, context={"request": request}
            )
            return Response(serializer.data)
        else:
            serializer = ProcessNoteSerializer(
                data=request.data, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(process=process)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch", "delete"], url_path=r"notes/(?P<note_id>\d+)")
    def note_detail(self, request, pk=None, note_id=None):
        process = self.get_object()
        note = process.notes.filter(id=note_id).first()
        if not note:
            return Response({"detail": "Nota não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        if request.method == "DELETE":
            note.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = ProcessNoteSerializer(
            note, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ─────────────────────────────────────────────────────────────────────────────
# Deadlines
# ─────────────────────────────────────────────────────────────────────────────

class DeadlineViewSet(ScopedModelViewSet):
    queryset = Deadline.objects.all()
    serializer_class = DeadlineSerializer
    required_perms_map = {
        "list":           ("deadlines.view_deadline",),
        "retrieve":       ("deadlines.view_deadline",),
        "create":         ("deadlines.add_deadline",),
        "update":         ("deadlines.change_deadline",),
        "partial_update": ("deadlines.change_deadline",),
        "destroy":        ("deadlines.delete_deadline",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if status_val := self.request.query_params.get("status"):
            qs = qs.filter(status=status_val)
        if priority := self.request.query_params.get("priority"):
            qs = qs.filter(priority=priority)
        if before := self.request.query_params.get("due_date_before"):
            qs = qs.filter(due_date__lte=before)
        if after := self.request.query_params.get("due_date_after"):
            qs = qs.filter(due_date__gte=after)
        return qs.select_related("responsible")


# ─────────────────────────────────────────────────────────────────────────────
# Documents
# ─────────────────────────────────────────────────────────────────────────────

class DocumentViewSet(ScopedModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    required_perms_map = {
        "list":           ("documents.view_document",),
        "retrieve":       ("documents.view_document",),
        "create":         ("documents.add_document",),
        "update":         ("documents.change_document",),
        "partial_update": ("documents.change_document",),
        "destroy":        ("documents.delete_document",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        if category := self.request.query_params.get("category"):
            qs = qs.filter(category=category)
        if status_val := self.request.query_params.get("status"):
            qs = qs.filter(status=status_val)
        if process := self.request.query_params.get("process"):
            qs = qs.filter(process_id=process)
        if customer := self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=customer)
        return qs.select_related("uploaded_by", "process", "customer")

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        if not getattr(self.request, "office", None):
            raise ValidationError({"detail": "Office não selecionado."})
        serializer.save(
            organization=self.request.organization,
            office=self.request.office,
            uploaded_by=self.request.user,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Finance
# ─────────────────────────────────────────────────────────────────────────────

class FeeAgreementViewSet(ScopedModelViewSet):
    queryset = FeeAgreement.objects.all()
    serializer_class = FeeAgreementSerializer
    required_perms_map = {
        "list":           ("finance.view_feeagreement",),
        "retrieve":       ("finance.view_feeagreement",),
        "create":         ("finance.add_feeagreement",),
        "update":         ("finance.change_feeagreement",),
        "partial_update": ("finance.change_feeagreement",),
        "destroy":        ("finance.delete_feeagreement",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if status_val := self.request.query_params.get("status"):
            qs = qs.filter(status=status_val)
        if customer := self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=customer)
        return qs.select_related("customer", "process", "responsible")


class InvoiceViewSet(ScopedModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    required_perms_map = {
        "list":           ("finance.view_invoice",),
        "retrieve":       ("finance.view_invoice",),
        "create":         ("finance.add_invoice",),
        "update":         ("finance.change_invoice",),
        "partial_update": ("finance.change_invoice",),
        "destroy":        ("finance.delete_invoice",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if status_val := self.request.query_params.get("status"):
            qs = qs.filter(status=status_val)
        if agreement := self.request.query_params.get("agreement"):
            qs = qs.filter(agreement_id=agreement)
        return qs.select_related("agreement__customer")


class PaymentViewSet(ScopedModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    required_perms_map = {
        "list":           ("finance.view_payment",),
        "retrieve":       ("finance.view_payment",),
        "create":         ("finance.add_payment",),
        "update":         ("finance.change_payment",),
        "partial_update": ("finance.change_payment",),
        "destroy":        ("finance.delete_payment",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if invoice := self.request.query_params.get("invoice"):
            qs = qs.filter(invoice_id=invoice)
        return qs.select_related("invoice__agreement__customer", "recorded_by")

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        if not getattr(self.request, "office", None):
            raise ValidationError({"detail": "Office não selecionado."})
        serializer.save(
            organization=self.request.organization,
            office=self.request.office,
            recorded_by=self.request.user,
        )


class ExpenseViewSet(ScopedModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    required_perms_map = {
        "list":           ("finance.view_expense",),
        "retrieve":       ("finance.view_expense",),
        "create":         ("finance.add_expense",),
        "update":         ("finance.change_expense",),
        "partial_update": ("finance.change_expense",),
        "destroy":        ("finance.delete_expense",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if status_val := self.request.query_params.get("status"):
            qs = qs.filter(status=status_val)
        if category := self.request.query_params.get("category"):
            qs = qs.filter(category=category)
        if month := self.request.query_params.get("month"):
            # format: YYYY-MM
            try:
                year, m = month.split("-")
                qs = qs.filter(date__year=year, date__month=m)
            except (ValueError, AttributeError):
                pass
        return qs.select_related("responsible")


class ProposalViewSet(ScopedModelViewSet):
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer
    required_perms_map = {
        "list":           ("finance.view_proposal",),
        "retrieve":       ("finance.view_proposal",),
        "create":         ("finance.add_proposal",),
        "update":         ("finance.change_proposal",),
        "partial_update": ("finance.change_proposal",),
        "destroy":        ("finance.delete_proposal",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if status_val := self.request.query_params.get("status"):
            qs = qs.filter(status=status_val)
        if customer := self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=customer)
        return qs.select_related("customer", "process", "responsible")

    @action(detail=True, methods=["post"], url_path="convert")
    def convert_to_agreement(self, request, pk=None):
        """Converte proposta aceita em FeeAgreement."""
        proposal = self.get_object()
        if proposal.status != "accepted":
            return Response(
                {"detail": "Apenas propostas com status 'accepted' podem ser convertidas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            agreement = proposal.convert_to_agreement()
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = FeeAgreementSerializer(agreement, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# Kanban
# ─────────────────────────────────────────────────────────────────────────────

class KanbanBoardView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        """Retorna o board completo do office (com colunas e cards)."""
        if not getattr(request, "office", None):
            return Response({"detail": "X-Office-Id obrigatório."}, status=400)
        board, _ = KanbanBoard.objects.get_or_create(
            organization=request.organization,
            office=request.office,
            defaults={"title": "Atividades"},
        )
        serializer = KanbanBoardSerializer(board)
        return Response(serializer.data)


class KanbanColumnViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInTenant, HasMembershipViewPerms]
    serializer_class = KanbanColumnSerializer
    required_perms_map = {
        "list":           ("portal.view_kanbancolumn",),
        "create":         ("portal.add_kanbancolumn",),
        "update":         ("portal.change_kanbancolumn",),
        "partial_update": ("portal.change_kanbancolumn",),
        "destroy":        ("portal.delete_kanbancolumn",),
    }

    def get_queryset(self):
        if not getattr(self.request, "office", None):
            return KanbanColumn.objects.none()
        board = KanbanBoard.objects.filter(
            organization=self.request.organization,
            office=self.request.office,
        ).first()
        if not board:
            return KanbanColumn.objects.none()
        return KanbanColumn.objects.filter(board=board).order_by("order", "id")

    def perform_create(self, serializer):
        board, _ = KanbanBoard.objects.get_or_create(
            organization=self.request.organization,
            office=self.request.office,
            defaults={"title": "Atividades"},
        )
        serializer.save(board=board)


class KanbanCardViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInTenant, HasMembershipViewPerms]
    serializer_class = KanbanCardSerializer
    required_perms_map = {
        "list":           ("portal.view_kanbancard",),
        "retrieve":       ("portal.view_kanbancard",),
        "create":         ("portal.add_kanbancard",),
        "update":         ("portal.change_kanbancard",),
        "partial_update": ("portal.change_kanbancard",),
        "destroy":        ("portal.delete_kanbancard",),
    }

    def get_queryset(self):
        if not getattr(self.request, "office", None):
            return KanbanCard.objects.none()
        board = KanbanBoard.objects.filter(
            organization=self.request.organization,
            office=self.request.office,
        ).first()
        if not board:
            return KanbanCard.objects.none()
        return KanbanCard.objects.filter(board=board).select_related("column", "created_by")

    def perform_create(self, serializer):
        board, _ = KanbanBoard.objects.get_or_create(
            organization=self.request.organization,
            office=self.request.office,
            defaults={"title": "Atividades"},
        )
        # auto-incrementa o number
        last = KanbanCard.objects.filter(board=board).order_by("-number").first()
        number = (last.number + 1) if last else 1
        serializer.save(board=board, number=number, created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        card = self.get_object()
        column_id = request.data.get("column_id")
        order = request.data.get("order", 0)
        if not column_id:
            return Response({"detail": "column_id obrigatório."}, status=400)
        column = KanbanColumn.objects.filter(id=column_id, board=card.board).first()
        if not column:
            return Response({"detail": "Coluna não encontrada neste board."}, status=404)
        card.column = column
        card.order = order
        card.save(update_fields=["column", "order"])
        return Response(KanbanCardSerializer(card, context={"request": request}).data)


# ─────────────────────────────────────────────────────────────────────────────
# Calendar
# ─────────────────────────────────────────────────────────────────────────────

class CalendarEntryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInTenant]
    serializer_class = CalendarEntrySerializer

    def get_queryset(self):
        if not getattr(self.request, "office", None):
            return CalendarEntry.objects.none()
        qs = CalendarEntry.objects.filter(
            organization=self.request.organization,
            office=self.request.office,
        )
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            qs = qs.filter(start__gte=start[:10])
        if end:
            qs = qs.filter(start__lte=end[:10])
        return qs.order_by("start")

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.organization,
            office=self.request.office,
            created_by=self.request.user,
        )


class CalendarTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInTenant]
    serializer_class = CalendarTemplateSerializer

    def get_queryset(self):
        if not getattr(self.request, "office", None):
            return CalendarEventTemplate.objects.none()
        return CalendarEventTemplate.objects.filter(
            organization=self.request.organization,
            office=self.request.office,
            is_active=True,
        ).order_by("title")

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.organization,
            office=self.request.office,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────────────────────────────────────

class UserSearchView(APIView):
    """GET /api/auth/users/search/?q=nome"""
    permission_classes = [IsInTenant]

    def get(self, request):
        from django.db import models as dj_models
        if not getattr(request, "office", None):
            return Response({"results": []})
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response({"results": []})
        from apps.memberships.models import Membership
        member_ids = Membership.objects.filter(
            office=request.office, is_active=True,
        ).values_list("user_id", flat=True)
        users = User.objects.filter(id__in=member_ids).filter(
            dj_models.Q(first_name__icontains=q) |
            dj_models.Q(last_name__icontains=q) |
            dj_models.Q(email__icontains=q)
        )[:10]
        return Response({"results": [
            {"id": u.id, "email": u.email,
             "name": f"{u.first_name} {u.last_name}".strip() or u.email}
            for u in users
        ]})

class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInTenant]
    serializer_class = TaskSerializer

    def get_queryset(self):
        if not getattr(self.request, "office", None):
            return Task.objects.none()
        qs = Task.objects.filter(
            organization=self.request.organization,
            office=self.request.office,
        ).select_related("assigned_to", "created_by")

        if status_val := self.request.query_params.get("status"):
            qs = qs.filter(status=status_val)
        if priority := self.request.query_params.get("priority"):
            qs = qs.filter(priority=priority)
        assigned = self.request.query_params.get("assigned_to")
        if assigned == "me":
            qs = qs.filter(assigned_to=self.request.user)
        elif assigned:
            qs = qs.filter(assigned_to_id=assigned)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.organization,
            office=self.request.office,
            created_by=self.request.user,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────────────────────

class NotificationListView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        if not getattr(request, "office", None):
            return Response({"detail": "X-Office-Id obrigatório."}, status=400)
        qs = Notification.objects.filter(
            organization=request.organization,
            office=request.office,
            user=request.user,
        ).order_by("-created_at")[:50]
        unread_count = Notification.objects.filter(
            organization=request.organization,
            office=request.office,
            user=request.user,
            is_read=False,
        ).count()
        serializer = NotificationSerializer(qs, many=True)
        return Response({
            "unread_count": unread_count,
            "results": serializer.data,
        })


class NotificationMarkReadView(APIView):
    permission_classes = [IsInTenant]

    def post(self, request, notif_id=None):
        if notif_id:
            Notification.objects.filter(
                id=notif_id, user=request.user,
                organization=request.organization,
                office=request.office,
            ).update(is_read=True)
        else:
            # mark-all
            Notification.objects.filter(
                user=request.user,
                organization=request.organization,
                office=request.office,
                is_read=False,
            ).update(is_read=True)

        unread = Notification.objects.filter(
            user=request.user,
            organization=request.organization,
            office=request.office,
            is_read=False,
        ).count()
        return Response({"ok": True, "unread_count": unread})


# ─────────────────────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────────────────────

class GlobalSearchView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response({"results": []})

        office = request.office
        org = request.organization
        if not office:
            return Response({"detail": "X-Office-Id obrigatório."}, status=400)
        results = []

        processes = Process.objects.filter(
            organization=org, office=office
        ).filter(Q(number__icontains=q) | Q(subject__icontains=q))[:5] 
        for p in processes:
            results.append({
                "type": "process", "id": p.id,
                "title": p.number, "subtitle": p.subject or "",
            })

        customers = Customer.objects.filter(
            organization=org, office=office, is_deleted=False
        ).filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(document__icontains=q)
        )[:5]
        for c in customers:
            results.append({
                "type": "customer", "id": c.id,
                "title": c.name, "subtitle": c.email or c.phone or "",
            })

        deadlines = Deadline.objects.filter(
            organization=org, office=office
        ).filter(Q(title__icontains=q) | Q(description__icontains=q))[:5]
        for d in deadlines:
            results.append({
                "type": "deadline", "id": d.id,
                "title": d.title, "subtitle": d.due_date.isoformat() if d.due_date else "",
            })

        documents = Document.objects.filter(
            organization=org, office=office
        ).filter(Q(title__icontains=q) | Q(description__icontains=q))[:5]
        for doc in documents:
            results.append({
                "type": "document", "id": doc.id,
                "title": doc.title, "subtitle": getattr(doc, "category", "") or "",
            })

        return Response({"results": results})


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

class DashboardView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        if not getattr(request, "office", None):
            return Response({"detail": "X-Office-Id obrigatório."}, status=400)

        org = request.organization
        office = request.office
        today = timezone.now().date()
        week_end = today + timezone.timedelta(days=7)
        month_start = today.replace(day=1)

        # Processes
        procs = Process.objects.filter(organization=org, office=office)
        proc_stats = {
            "total": procs.count(),
            "active": procs.filter(status="active").count(),
            "suspended": procs.filter(status="suspended").count(),
            "finished": procs.filter(status="finished").count(),
        }

        # Deadlines
        deadlines = Deadline.objects.filter(organization=org, office=office)
        dl_stats = {
            "overdue": deadlines.filter(due_date__lt=today, status="pending").count(),
            "today": deadlines.filter(due_date=today, status="pending").count(),
            "this_week": deadlines.filter(
                due_date__gte=today, due_date__lte=week_end, status="pending"
            ).count(),
            "total_pending": deadlines.filter(status="pending").count(),
        }

        # Finance
        invoices = Invoice.objects.filter(organization=org, office=office)
        expenses = Expense.objects.filter(organization=org, office=office)

        receivable = (
            invoices.exclude(status__in=["paid", "cancelled"])
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        received_month = (
            Payment.objects.filter(
                organization=org, office=office,
                paid_at__gte=month_start,
            ).aggregate(total=Sum("amount"))["total"] or 0
        )
        expenses_month = (
            expenses.filter(date__gte=month_start)
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        fin_stats = {
            "receivable": str(receivable),
            "received_month": str(received_month),
            "pending_invoices": invoices.exclude(status__in=["paid", "cancelled"]).count(),
            "expenses_month": str(expenses_month),
        }

        # Customers
        customers = Customer.objects.filter(organization=org, office=office, is_deleted=False)
        cust_stats = {
            "total": customers.count(),
            "leads": customers.filter(status="lead").count(),
            "clients": customers.filter(status="client").count(),
        }

        # Recent activity
        recent = (ActivityEvent.objects.filter(organization=org, office=office)
                  .select_related("actor")
                  .order_by("-created_at")[:10]
                  )

        def _time_ago(dt):
            diff = timezone.now() - dt
            s = int(diff.total_seconds())
            if s < 3600:
                return f"{s // 60}min atrás"
            if s < 86400:
                return f"{s // 3600}h atrás"
            return f"{s // 86400}d atrás"

        def _event_verb(ev: ActivityEvent) -> str:
            try:
                if  isinstance(ev.changes, dict) and ev.changes.get("verb"):
                    return str(ev.changes["verb"])
            except Exception:
                pass
            return getattr(ev, "action", "") or "custom"
        
        def _event_description(ev: ActivityEvent) -> str:
            s = (getattr(ev, "summary", "") or "").strip()
            if s:
                return s
            try:
                if isinstance(ev.changes, dict) and ev.changes.get("detail"):
                    return str(ev.changes["detail"])[:500]
            except Exception:
                pass
            return "-"
        
        def _event_actor_name(ev: ActivityEvent) -> str:
            if ev.actor:
                name = (ev.actor.get_full_name() or ev.actor.email or "").strip()
                if name:
                    return name
            name = (getattr(ev, "actor_name", "") or "").strip()
            return name or "Sistema"

        activity = [
            {
                "verb": _event_verb(a),
                "description": _event_description(a),
                "actor": _event_actor_name(a),
                "when": _time_ago(a.created_at),
            }
            for a in recent
        ]

        return Response({
            "processes": proc_stats,
            "deadlines": dl_stats,
            "finance": fin_stats,
            "customers": cust_stats,
            "recent_activity": activity,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Invite
# ─────────────────────────────────────────────────────────────────────────────
User = get_user_model()

def _make_invite_url(request, token: str) -> str:
    # você controla onde o front roda
    front_base = (getattr(request, "frontend_base_url", None) or
                  request.headers.get("X-Frontend-Base") or
                  "http://localhost:5173")
    return f"{front_base.rstrip('/')}/invite/{token}"


class InvitationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # ✅ aqui você decide quem pode convidar
        # Exemplo: só admin/manager
        membership = getattr(request, "membership", None)
        if not membership or getattr(membership, "role", "") not in ("admin", "manager"):
            return Response({"detail": "Sem permissão para convidar."}, status=403)

        ser = InvitationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        email = ser.validated_data["email"].strip().lower()
        role = ser.validated_data["role"]
        ttl_hours = ser.validated_data.get("ttl_hours", 72)

        office = None
        office_id = ser.validated_data.get("office_id", None)
        if office_id:
            # se você tem Office model em portal:
            from apps.offices.models import Office
            office = Office.objects.filter(id=office_id, organization=request.organization).first()
            if not office:
                return Response({"detail": "Office inválido."}, status=400)

        inv, raw = Invitation.create_invite(
            organization=request.organization,
            office=office,
            email=email,
            role=role,
            invited_by=request.user,
            ttl_hours=ttl_hours,
        )

        return Response(
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "expires_at": inv.expires_at,
                "invite_url": _make_invite_url(request, raw),
                "token": raw,  # opcional: útil se você vai mandar email no front
            },
            status=201,
        )


class InvitationRetrievePublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token: str):
        token_hash = Invitation._hash_token(token)
        inv = Invitation.objects.select_related("organization", "office").filter(token_hash=token_hash).first()
        if not inv:
            return Response({"detail": "Convite inválido."}, status=404)

        inv.mark_expired_if_needed()
        if not inv.is_valid():
            return Response({"detail": f"Convite {inv.status}."}, status=400)

        return Response(InvitationPublicSerializer(inv).data, status=200)


class InvitationAcceptView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request, token: str):
        token_hash = Invitation._hash_token(token)
        inv = Invitation.objects.select_related("organization", "office").select_for_update().filter(token_hash=token_hash).first()
        if not inv:
            return Response({"detail": "Convite inválido."}, status=404)

        inv.mark_expired_if_needed()
        if not inv.is_valid():
            return Response({"detail": f"Convite {inv.status}."}, status=400)

        ser = InvitationAcceptSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        password = ser.validated_data["password"]
        full_name = (ser.validated_data.get("full_name") or "").strip()

        # 1) cria ou busca usuário
        user = User.objects.filter(email__iexact=inv.email).first()
        if not user:
            user = User.objects.create_user(email=inv.email, password=password)
        else:
            # se já existe, só define senha (ou você pode exigir login do usuário)
            user.set_password(password)
            user.save(update_fields=["password"])

        if full_name and hasattr(user, "first_name"):
            # se seu User for o padrão do Django: split simples
            parts = full_name.split()
            user.first_name = parts[0]
            user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            user.save(update_fields=["first_name", "last_name"])

        # 2) cria membership (ajuste para seu model real)
        from apps.memberships.models import Membership  # ajuste o nome real do seu model

        Membership.objects.update_or_create(
            organization=inv.organization,
            user=user,
            defaults={
                "office": inv.office,
                "role": inv.role,
                "is_active": True,
            },
        )

        # 3) marca convite como aceito
        inv.status = "accepted"
        inv.accepted_at = timezone.now()
        inv.accepted_by_user = user
        inv.save(update_fields=["status", "accepted_at", "accepted_by_user"])

        # 4) opcional: devolver JWT já logado
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "detail": "Convite aceito.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=200,
        )