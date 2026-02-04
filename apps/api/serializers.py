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

    class Meta:
        model = Process
        fields = ["id", "number", "court", "subject", "phase", "status", "created_at", "updated_at", "parties"]

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
    class Meta:
        model = Deadline
        fields = ["id", "title", "due_date", "type", "priority", "description", "responsible", "created_at", "updated_at"]

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
