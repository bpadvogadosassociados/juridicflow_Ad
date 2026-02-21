from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from apps.shared.models import AuditLog
from apps.memberships.models import Membership
from apps.offices.models import Office
from apps.customers.models import Customer
from apps.processes.models import Process
from apps.deadlines.models import Deadline
from apps.documents.models import Document
from apps.finance.models import FeeAgreement, Invoice

from .serializers import (
    MeSerializer, MembershipSerializer, OfficeSerializer,
    CustomerSerializer, ProcessSerializer, DeadlineSerializer, DocumentSerializer,
    FeeAgreementSerializer, InvoiceSerializer
)
from .permissions import IsInTenant, IsOfficeAdminOrAbove

def _ip(request):
    return request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({"detail": "Credenciais inválidas."}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        AuditLog.objects.create(user=user, action="login", ip_address=_ip(request))
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})

class MeView(APIView):
    def get(self, request):
        return Response(MeSerializer(request.user).data)

class MembershipsView(APIView):
    def get(self, request):
        qs = Membership.objects.filter(user=request.user, is_active=True).select_related("organization", "office")
        return Response(MembershipSerializer(qs, many=True).data)

class OfficesView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        m = request.membership
        if m.office_id:
            offices = Office.objects.filter(id=m.office_id)
        else:
            offices = Office.objects.filter(organization=request.organization, is_active=True)
        return Response(OfficeSerializer(offices, many=True).data)

class ScopedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInTenant]

    def get_queryset(self):
        org = self.request.organization
        office = self.request.office
        m = self.request.membership
        qs = super().get_queryset().filter(organization=org)
        if office:
            return qs.filter(office=office)
        if m.role == "org_admin" and m.office_id is None:
            return qs
        return qs.none()

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        org = self.request.organization
        office = self.request.office
        m = self.request.membership
        if not office and not (m.role == "org_admin" and m.office_id is None):
            raise ValidationError({"detail": "Office não selecionado. Envie header X-Office-Id."})
        serializer.save(organization=org, office=office)

class CustomerViewSet(ScopedModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

class ProcessViewSet(ScopedModelViewSet):
    queryset = Process.objects.all()
    serializer_class = ProcessSerializer

class DeadlineViewSet(ScopedModelViewSet):
    queryset = Deadline.objects.all()
    serializer_class = DeadlineSerializer

class DocumentViewSet(ScopedModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        org = self.request.organization
        office = self.request.office
        m = self.request.membership
        if not office and not (m.role == "org_admin" and m.office_id is None):
            raise ValidationError({"detail": "Office não selecionado. Envie header X-Office-Id."})
        serializer.save(organization=org, office=office, uploaded_by=self.request.user)

class FeeAgreementViewSet(ScopedModelViewSet):
    queryset = FeeAgreement.objects.all()
    serializer_class = FeeAgreementSerializer
    permission_classes = [IsInTenant, IsOfficeAdminOrAbove]

class InvoiceViewSet(ScopedModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsInTenant, IsOfficeAdminOrAbove]
