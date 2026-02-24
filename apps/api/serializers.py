from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.offices.models import Office
from apps.memberships.models import Membership
from apps.customers.models import Customer, CustomerInteraction, CustomerRelationship
from apps.processes.models import Process, ProcessParty, ProcessNote
from apps.deadlines.models import Deadline
from apps.documents.models import Document
from apps.finance.models import FeeAgreement, Invoice, Payment, Expense, Proposal
from apps.portal.models import (
    KanbanBoard, KanbanColumn, KanbanCard,
    CalendarEntry, CalendarEventTemplate,
    Notification, Task,
)

UserModel = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class UserMinimalSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = ["id", "email", "first_name", "last_name", "full_name"]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


# ─────────────────────────────────────────────────────────────────────────────
# Auth / Org
# ─────────────────────────────────────────────────────────────────────────────

class OfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = ["id", "name", "is_active", "organization_id"]


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "plan", "is_active"]


class MembershipSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    office = OfficeSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "role", "is_active", "organization", "office"]


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "is_staff"]


# ─────────────────────────────────────────────────────────────────────────────
# Customers
# ─────────────────────────────────────────────────────────────────────────────

class CustomerSerializer(serializers.ModelSerializer):
    responsible_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            # Dados básicos
            "name", "document", "type", "status",
            # Contato
            "email", "phone", "phone_secondary", "whatsapp",
            # Endereço
            "address_street", "address_number", "address_complement",
            "address_neighborhood", "address_city", "address_state", "address_zipcode",
            # PF
            "profession", "birth_date", "nationality", "marital_status",
            # PJ
            "company_name", "state_registration", "municipal_registration",
            # CRM
            "origin", "referral_name", "tags",
            "notes", "internal_notes",
            "responsible", "responsible_name",
            "first_contact_date", "last_interaction_date",
            # Pipeline
            "pipeline_stage", "next_action", "next_action_date",
            "estimated_value", "loss_reason",
            # LGPD
            "can_whatsapp", "can_email", "lgpd_consent_date",
            # Timestamps
            "created_at", "updated_at",
        ]
        read_only_fields = ["responsible_name", "created_at", "updated_at"]

    def get_responsible_name(self, obj):
        if obj.responsible:
            return obj.responsible.get_full_name() or obj.responsible.email
        return None


class CustomerInteractionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerInteraction
        fields = [
            "id", "type", "date", "subject", "description",
            "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = ["created_by", "created_by_name", "created_at"]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)


class CustomerRelationshipSerializer(serializers.ModelSerializer):
    to_customer_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerRelationship
        fields = [
            "id", "from_customer", "to_customer", "to_customer_name",
            "relation_type", "notes", "created_at",
        ]
        read_only_fields = ["to_customer_name", "created_at"]

    def get_to_customer_name(self, obj):
        return obj.to_customer.name


# ─────────────────────────────────────────────────────────────────────────────
# Processes
# ─────────────────────────────────────────────────────────────────────────────

class ProcessPartySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessParty
        fields = [
            "id", "role", "customer", "name",
            "document", "email", "phone", "notes",
        ]


class ProcessNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ProcessNote
        fields = [
            "id", "text", "is_private",
            "author", "author_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["author", "author_name", "created_at", "updated_at"]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.email
        return None

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)


class ProcessSerializer(serializers.ModelSerializer):
    parties = ProcessPartySerializer(many=True, required=False)
    responsible_name = serializers.SerializerMethodField()
    deadlines_count = serializers.SerializerMethodField()
    next_deadline = serializers.SerializerMethodField()

    class Meta:
        model = Process
        fields = [
            "id",
            # Identificação
            "number", "court", "subject",
            # Status
            "phase", "status", "area",
            # Dados jurídicos
            "description", "cause_value",
            "filing_date", "distribution_date", "first_hearing_date",
            "sentence_date", "court_unit", "judge_name",
            # Avaliação
            "risk", "success_probability",
            # Controle
            "tags", "internal_notes",
            "next_action", "last_movement", "last_movement_date",
            # Responsável
            "responsible", "responsible_name",
            # Nested
            "parties",
            # Computed
            "deadlines_count", "next_deadline",
            # Timestamps
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "responsible_name", "deadlines_count",
            "next_deadline", "created_at", "updated_at",
        ]

    def validate_number(self, value):
        from apps.processes.models import validate_cnj
        validate_cnj(value)
        return value

    def get_responsible_name(self, obj):
        if obj.responsible:
            return obj.responsible.get_full_name() or obj.responsible.email
        return None

    def get_deadlines_count(self, obj):
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Process)
        return Deadline.objects.filter(content_type=ct, object_id=obj.id).count()

    def get_next_deadline(self, obj):
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone
        ct = ContentType.objects.get_for_model(Process)
        dl = Deadline.objects.filter(
            content_type=ct, object_id=obj.id,
            due_date__gte=timezone.now().date(),
            status="pending",
        ).order_by("due_date").first()
        if dl:
            return {
                "id": dl.id, "title": dl.title,
                "due_date": dl.due_date.isoformat(), "priority": dl.priority,
            }
        return None

    def create(self, validated_data):
        parties = validated_data.pop("parties", [])
        process = Process.objects.create(**validated_data)
        for p in parties:
            ProcessParty.objects.create(process=process, **p)
        return process

    def update(self, instance, validated_data):
        parties = validated_data.pop("parties", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if parties is not None:
            instance.parties.all().delete()
            for p in parties:
                ProcessParty.objects.create(process=instance, **p)
        return instance


# ─────────────────────────────────────────────────────────────────────────────
# Deadlines
# ─────────────────────────────────────────────────────────────────────────────

class DeadlineSerializer(serializers.ModelSerializer):
    responsible_name = serializers.SerializerMethodField()
    related_process = serializers.SerializerMethodField()
    status_info = serializers.SerializerMethodField()
    # write-only helper to link a process
    process_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Deadline
        fields = [
            "id", "title", "due_date", "type", "priority",
            "status",            # ← campo que estava AUSENTE na versão original
            "description",
            "responsible", "responsible_name",
            "process_id",        # write
            "related_process",   # read
            "status_info",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "responsible_name", "related_process",
            "status_info", "created_at", "updated_at",
        ]

    def get_responsible_name(self, obj):
        if obj.responsible:
            return obj.responsible.get_full_name() or obj.responsible.email
        return None

    def get_related_process(self, obj):
        from django.contrib.contenttypes.models import ContentType
        if obj.content_type and obj.object_id:
            ct_process = ContentType.objects.get_for_model(Process)
            if obj.content_type == ct_process:
                try:
                    p = Process.objects.get(id=obj.object_id)
                    return {"id": p.id, "number": p.number, "subject": p.subject or ""}
                except Process.DoesNotExist:
                    pass
        return None

    def get_status_info(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        if obj.due_date < today:
            return {"label": "overdue", "text": "Atrasado", "class": "danger"}
        elif obj.due_date == today:
            return {"label": "today", "text": "Vence hoje", "class": "warning"}
        else:
            days = (obj.due_date - today).days
            label = "soon" if days <= 3 else "future"
            return {"label": label, "text": f"Em {days} dias", "class": "info" if days <= 3 else "secondary"}

    def create(self, validated_data):
        process_id = validated_data.pop("process_id", None)
        deadline = Deadline.objects.create(**validated_data)
        if process_id:
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(Process)
            deadline.content_type = ct
            deadline.object_id = process_id
            deadline.save(update_fields=["content_type", "object_id"])
        return deadline

    def update(self, instance, validated_data):
        process_id = validated_data.pop("process_id", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if process_id is not None:
            if process_id:
                from django.contrib.contenttypes.models import ContentType
                ct = ContentType.objects.get_for_model(Process)
                instance.content_type = ct
                instance.object_id = process_id
            else:
                instance.content_type = None
                instance.object_id = None
        instance.save()
        return instance


# ─────────────────────────────────────────────────────────────────────────────
# Documents
# ─────────────────────────────────────────────────────────────────────────────

class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "title", "description", "file", "file_url",
            "uploaded_by", "created_at", "updated_at",
        ]
        read_only_fields = ["uploaded_by", "file_url", "created_at", "updated_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        return request.build_absolute_uri(obj.file.url) if obj.file else None


# ─────────────────────────────────────────────────────────────────────────────
# Finance
# ─────────────────────────────────────────────────────────────────────────────

class FeeAgreementSerializer(serializers.ModelSerializer):
    total_invoiced = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)
    total_received = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = FeeAgreement
        fields = [
            "id", "customer", "process",
            "title", "description",
            "amount", "billing_type", "installments",
            "status",
            "start_date", "end_date",
            "notes", "responsible",
            "total_invoiced", "total_received", "balance",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "total_invoiced", "total_received", "balance",
            "created_at", "updated_at",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    net_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "agreement",
            "number", "issue_date", "due_date",
            "amount", "discount",
            "status", "description", "notes", "payment_method",
            "net_amount", "paid_amount", "balance", "is_overdue",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "net_amount", "paid_amount", "balance",
            "is_overdue", "created_at", "updated_at",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id", "invoice",
            "paid_at", "amount", "method",
            "reference", "notes",
            "recorded_by", "recorded_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "recorded_by", "recorded_by_name",
            "created_at", "updated_at",
        ]

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return obj.recorded_by.get_full_name() or obj.recorded_by.email
        return None

    def create(self, validated_data):
        validated_data["recorded_by"] = self.context["request"].user
        return super().create(validated_data)


class ExpenseSerializer(serializers.ModelSerializer):
    responsible_name = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            "id", "title", "description",
            "category", "date", "due_date",
            "amount", "status",
            "payment_method", "supplier", "reference",
            "notes", "responsible", "responsible_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["responsible_name", "created_at", "updated_at"]

    def get_responsible_name(self, obj):
        if obj.responsible:
            return obj.responsible.get_full_name() or obj.responsible.email
        return None


class ProposalSerializer(serializers.ModelSerializer):
    responsible_name = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = [
            "id", "title", "description",
            "amount", "status",
            "issue_date", "valid_until",
            "customer", "process", "responsible", "responsible_name",
            "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["responsible_name", "created_at", "updated_at"]

    def get_responsible_name(self, obj):
        if obj.responsible:
            return obj.responsible.get_full_name() or obj.responsible.email
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Kanban
# ─────────────────────────────────────────────────────────────────────────────

class KanbanCardSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = KanbanCard
        fields = [
            "id", "number", "title", "body_md",
            "order", "column",
            "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = ["number", "created_by", "created_by_name", "created_at"]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None


class KanbanColumnSerializer(serializers.ModelSerializer):
    cards = KanbanCardSerializer(many=True, read_only=True)

    class Meta:
        model = KanbanColumn
        fields = ["id", "title", "order", "cards"]


class KanbanBoardSerializer(serializers.ModelSerializer):
    columns = KanbanColumnSerializer(many=True, read_only=True)

    class Meta:
        model = KanbanBoard
        fields = ["id", "title", "columns"]


# ─────────────────────────────────────────────────────────────────────────────
# Calendar
# ─────────────────────────────────────────────────────────────────────────────

class CalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = [
            "id", "title", "start", "end",
            "all_day", "color",
            "created_by", "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class CalendarTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEventTemplate
        fields = ["id", "title", "color", "is_active", "created_at"]
        read_only_fields = ["created_at"]


# ─────────────────────────────────────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────────────────────────────────────

class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "title", "description",
            "status", "priority",
            "assigned_to", "assigned_to_name",
            "due_date",
            "created_by", "created_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "created_by", "created_by_name",
            "assigned_to_name", "created_at", "updated_at",
        ]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.email
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


# ─────────────────────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────────────────────

def _time_ago(dt):
    from django.utils import timezone
    diff = timezone.now() - dt
    secs = int(diff.total_seconds())
    if secs < 60:
        return "agora"
    elif secs < 3600:
        return f"{secs // 60}min atrás"
    elif secs < 86400:
        return f"{secs // 3600}h atrás"
    return f"{secs // 86400}d atrás"


class NotificationSerializer(serializers.ModelSerializer):
    when = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id", "title", "message", "type",
            "is_read", "url",
            "when", "created_at",
        ]
        read_only_fields = ["when", "created_at"]

    def get_when(self, obj):
        return _time_ago(obj.created_at)
