from rest_framework import serializers
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.offices.models import Office
from apps.memberships.models import Membership
from apps.customers.models import Customer
from apps.processes.models import Process, ProcessParty
from apps.deadlines.models import Deadline
from apps.documents.models import Document
from apps.finance.models import FeeAgreement, Invoice

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

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "document", "type", "email", "phone", "notes", "created_at", "updated_at"]

class ProcessPartySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessParty
        fields = ["id", "role", "customer", "name"]

class ProcessSerializer(serializers.ModelSerializer):
    parties = ProcessPartySerializer(many=True, required=False)
    deadlines_count = serializers.SerializerMethodField()
    next_deadline = serializers.SerializerMethodField()
    
    class Meta:
        model = Process
        fields = [
            "id", "number", "court", "subject", "phase",
            "status", "created_at", "updated_at",
            "parties", "deadlines_count", "next_deadline"
        ]
    
    def validate_number(self, value):
        """Valida número CNJ na API"""
        from apps.processes.models import validate_cnj
        validate_cnj(value)
        return value
    
    def get_deadlines_count(self, obj):
        """Retorna quantidade de prazos vinculados"""
        from django.contrib.contenttypes.models import ContentType
        from apps.deadlines.models import Deadline
        
        ct = ContentType.objects.get_for_model(Process)
        return Deadline.objects.filter(
            content_type=ct,
            object_id=obj.id
        ).count()
    
    def get_next_deadline(self, obj):
        """Retorna próximo prazo do processo"""
        from django.contrib.contenttypes.models import ContentType
        from apps.deadlines.models import Deadline
        from django.utils import timezone
        
        ct = ContentType.objects.get_for_model(Process)
        next_dl = Deadline.objects.filter(
            content_type=ct,
            object_id=obj.id,
            due_date__gte=timezone.now().date()
        ).order_by('due_date').first()
        
        if next_dl:
            return {
                "id": next_dl.id,
                "title": next_dl.title,
                "due_date": next_dl.due_date.isoformat(),
                "priority": next_dl.priority
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

class DeadlineSerializer(serializers.ModelSerializer):
    related_process = serializers.SerializerMethodField()
    responsible_name = serializers.SerializerMethodField()
    status_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Deadline
        fields = [
            "id", "title", "due_date", "type", "priority",
            "description", "responsible", "responsible_name",
            "created_at", "updated_at",
            "related_process", "status_info"
        ]

    def get_responsible_name(self, obj):
        """Nome do responsável"""
        if obj.responsible:
            return obj.responsible.get_full_name() or obj.responsible.email
        return None
    
    def get_related_process(self, obj):
        """Retorna processo vinculado se existir"""
        from django.contrib.contenttypes.models import ContentType
        from apps.processes.models import Process
        
        if obj.content_type and obj.object_id:
            ct_process = ContentType.objects.get_for_model(Process)
            if obj.content_type == ct_process:
                try:
                    process = Process.objects.get(id=obj.object_id)
                    return {
                        "id": process.id,
                        "number": process.number,
                        "subject": process.subject or ""
                    }
                except Process.DoesNotExist:
                    pass
        return None
    
    def get_status_info(self, obj):
        """Status calculado (atrasado, hoje, futuro)"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if obj.due_date < today:
            return {"label": "overdue", "text": "Atrasado", "class": "danger"}
        elif obj.due_date == today:
            return {"label": "today", "text": "Vence hoje", "class": "warning"}
        else:
            days = (obj.due_date - today).days
            if days <= 3:
                return {"label": "soon", "text": f"Em {days} dias", "class": "info"}
            else:
                return {"label": "future", "text": f"Em {days} dias", "class": "secondary"}

class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "title", "description", "file", "file_url", "uploaded_by", "created_at", "updated_at"]
        read_only_fields = ["uploaded_by"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        return request.build_absolute_uri(obj.file.url) if obj.file else None

class FeeAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeAgreement
        fields = ["id", "customer", "process", "title", "amount", "billing_type", "notes", "created_at", "updated_at"]

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "agreement", "issue_date", "due_date", "amount", "status", "created_at", "updated_at"]
