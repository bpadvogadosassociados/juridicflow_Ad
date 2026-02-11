"""
Validadores de CPF e CNPJ com verificação de dígitos.

Uso em models:
    from apps.core.validators import validate_cpf_cnpj
    document = models.CharField(max_length=18, validators=[validate_cpf_cnpj])

Uso direto:
    from apps.core.validators import validate_cpf, validate_cnpj
    is_valid = validate_cpf("123.456.789-09")
"""
import re
from django.core.exceptions import ValidationError


def _only_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def validate_cpf(value: str) -> bool:
    """
    Valida CPF com dígitos verificadores.
    Aceita com ou sem formatação (123.456.789-09 ou 12345678909).
    """
    digits = _only_digits(value)

    if len(digits) != 11:
        return False

    # Rejeita sequências repetidas (111.111.111-11, etc.)
    if digits == digits[0] * 11:
        return False

    # Primeiro dígito verificador
    weights_1 = [10, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights_1[i] for i in range(9))
    remainder = total % 11
    check_1 = 0 if remainder < 2 else 11 - remainder
    if int(digits[9]) != check_1:
        return False

    # Segundo dígito verificador
    weights_2 = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights_2[i] for i in range(10))
    remainder = total % 11
    check_2 = 0 if remainder < 2 else 11 - remainder
    if int(digits[10]) != check_2:
        return False

    return True


def validate_cnpj(value: str) -> bool:
    """
    Valida CNPJ com dígitos verificadores.
    Aceita com ou sem formatação (12.345.678/0001-95 ou 12345678000195).
    """
    digits = _only_digits(value)

    if len(digits) != 14:
        return False

    # Rejeita sequências repetidas
    if digits == digits[0] * 14:
        return False

    # Primeiro dígito verificador
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights_1[i] for i in range(12))
    remainder = total % 11
    check_1 = 0 if remainder < 2 else 11 - remainder
    if int(digits[12]) != check_1:
        return False

    # Segundo dígito verificador
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights_2[i] for i in range(13))
    remainder = total % 11
    check_2 = 0 if remainder < 2 else 11 - remainder
    if int(digits[13]) != check_2:
        return False

    return True


def validate_cpf_cnpj(value: str):
    """
    Django validator para campo de documento (CPF ou CNPJ).
    Levanta ValidationError se inválido.
    """
    if not value:
        return  # Campo pode ser blank — deixa o blank=True/required tratar

    digits = _only_digits(value)

    if len(digits) == 11:
        if not validate_cpf(value):
            raise ValidationError(
                "CPF inválido: %(value)s",
                params={"value": value},
                code="invalid_cpf",
            )
    elif len(digits) == 14:
        if not validate_cnpj(value):
            raise ValidationError(
                "CNPJ inválido: %(value)s",
                params={"value": value},
                code="invalid_cnpj",
            )
    else:
        raise ValidationError(
            "Documento deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ). Recebido: %(length)s dígitos.",
            params={"length": len(digits)},
            code="invalid_document_length",
        )


def format_cpf(value: str) -> str:
    """Formata CPF: 12345678909 → 123.456.789-09"""
    d = _only_digits(value)
    if len(d) != 11:
        return value
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def format_cnpj(value: str) -> str:
    """Formata CNPJ: 12345678000195 → 12.345.678/0001-95"""
    d = _only_digits(value)
    if len(d) != 14:
        return value
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def format_document(value: str) -> str:
    """Formata CPF ou CNPJ automaticamente."""
    d = _only_digits(value)
    if len(d) == 11:
        return format_cpf(value)
    elif len(d) == 14:
        return format_cnpj(value)
    return value