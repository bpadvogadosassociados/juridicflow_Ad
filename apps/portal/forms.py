from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

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
            raise ValidationError("Este login é apenas para usuários finais. Use o /admin para contas administrativas.")
        if not user.is_active:
            raise ValidationError("Usuário desativado.")
        data["user"] = user
        return data

class SupportTicketForm(forms.Form):
    subject = forms.CharField(max_length=120, label="Assunto")
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 6}), label="Mensagem")

class ThemeForm(forms.Form):
    theme = forms.ChoiceField(choices=[
        ("default", "Padrão (Dark)"),
        ("dark", "Dark"),
        ("light", "Claro"),
    ], label="Tema")
