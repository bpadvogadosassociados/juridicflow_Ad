"""
Forms do Portal — validação e limpeza de dados.
"""
from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from apps.customers.models import Customer
from apps.documents.models import Document
from apps.finance.models import FeeAgreement, Expense


# ==================== AUTH ====================

class PortalLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return data
        user = authenticate(username=email, password=password)
        if not user:
            raise ValidationError("Email ou senha inválidos.")
        if user.is_staff or user.is_superuser:
            raise ValidationError(
                "Este login é apenas para usuários finais. Use o /admin para contas administrativas."
            )
        if not user.is_active:
            raise ValidationError("Usuário desativado.")
        data["user"] = user
        return data


class SupportTicketForm(forms.Form):
    subject = forms.CharField(max_length=120, label="Assunto")
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 6}), label="Mensagem")


class ThemeForm(forms.Form):
    theme = forms.ChoiceField(
        choices=[
            ("default", "Padrão (Dark)"),
            ("dark", "Dark"),
            ("light", "Claro"),
        ],
        label="Tema",
    )


# ==================== CUSTOMER ====================

class CustomerForm(forms.ModelForm):
    """Form para criação e edição de Contatos/Clientes."""

    class Meta:
        model = Customer
        fields = [
            "name", "document", "type", "status",
            "email", "phone", "phone_secondary", "whatsapp",
            "address_street", "address_number", "address_complement",
            "address_neighborhood", "address_city", "address_state", "address_zipcode",
            "profession", "birth_date", "nationality", "marital_status",
            "company_name", "state_registration", "municipal_registration",
            "origin", "referral_name", "tags",
            "notes", "internal_notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome completo ou Razão Social"}),
            "document": forms.TextInput(attrs={"class": "form-control", "placeholder": "CPF ou CNPJ"}),
            "type": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "(XX) XXXXX-XXXX"}),
            "phone_secondary": forms.TextInput(attrs={"class": "form-control"}),
            "whatsapp": forms.TextInput(attrs={"class": "form-control"}),
            "address_street": forms.TextInput(attrs={"class": "form-control"}),
            "address_number": forms.TextInput(attrs={"class": "form-control"}),
            "address_complement": forms.TextInput(attrs={"class": "form-control"}),
            "address_neighborhood": forms.TextInput(attrs={"class": "form-control"}),
            "address_city": forms.TextInput(attrs={"class": "form-control"}),
            "address_state": forms.TextInput(attrs={"class": "form-control", "maxlength": "2"}),
            "address_zipcode": forms.TextInput(attrs={"class": "form-control", "placeholder": "00000-000"}),
            "profession": forms.TextInput(attrs={"class": "form-control"}),
            "birth_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "nationality": forms.TextInput(attrs={"class": "form-control"}),
            "marital_status": forms.TextInput(attrs={"class": "form-control"}),
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "state_registration": forms.TextInput(attrs={"class": "form-control"}),
            "municipal_registration": forms.TextInput(attrs={"class": "form-control"}),
            "origin": forms.Select(attrs={"class": "form-control"}),
            "referral_name": forms.TextInput(attrs={"class": "form-control"}),
            "tags": forms.TextInput(attrs={"class": "form-control", "placeholder": "vip, urgente, trabalhista"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "internal_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise ValidationError("Nome é obrigatório.")
        return name


# ==================== DOCUMENT UPLOAD ====================

class DocumentUploadForm(forms.ModelForm):
    """Form para upload de documentos."""

    process_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    customer_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    folder_id = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Document
        fields = [
            "title", "description", "category", "status",
            "file", "tags", "is_confidential", "is_template",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "tags": forms.TextInput(attrs={"class": "form-control"}),
        }


# ==================== FEE AGREEMENT ====================

class FeeAgreementForm(forms.ModelForm):
    """Form para criação de contratos de honorários."""

    class Meta:
        model = FeeAgreement
        fields = [
            "customer", "title", "description", "amount",
            "billing_type", "installments", "status",
            "start_date", "end_date", "notes",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "billing_type": forms.Select(attrs={"class": "form-control"}),
            "installments": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, office=None, **kwargs):
        super().__init__(*args, **kwargs)
        if office:
            self.fields["customer"].queryset = Customer.objects.filter(
                office=office, is_deleted=False
            ).order_by("name")