from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    Publication, JudicialEvent, ProcessMonitoring,
    PublicationRule, PublicationFilter, PublicationImport,
)

User = get_user_model()


class UserMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name"]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


# ─────────────────────────────────────────────────────────────────────────────
# Publication
# ─────────────────────────────────────────────────────────────────────────────

class PublicationSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    imported_by = UserMiniSerializer(read_only=True)
    text_preview = serializers.CharField(read_only=True)
    events_count = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = [
            "id", "source", "source_display", "source_id",
            "raw_text", "text_preview", "publication_date",
            "import_date", "process_cnj", "process",
            "metadata", "imported_by", "events_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["content_hash", "import_date", "created_at", "updated_at"]

    def get_events_count(self, obj):
        return obj.events.count()


class PublicationCreateSerializer(serializers.ModelSerializer):
    """Usado apenas para criação manual de publicações."""
    class Meta:
        model = Publication
        fields = [
            "source", "source_id", "raw_text", "publication_date",
            "process_cnj", "process", "original_file", "metadata",
        ]


# ─────────────────────────────────────────────────────────────────────────────
# JudicialEvent
# ─────────────────────────────────────────────────────────────────────────────

class JudicialEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    urgency_display = serializers.CharField(source="get_urgency_display", read_only=True)
    assigned_to = UserMiniSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        # queryset é definido dinamicamente no __init__ para evitar
        # atribuição cross-tenant (falha de segurança).
        queryset=User.objects.none(), source="assigned_to",
        write_only=True, allow_null=True, required=False,
    )

    # Campos derivados para facilitar o front
    process_cnj = serializers.CharField(source="publication.process_cnj", read_only=True)
    publication_date = serializers.DateField(source="publication.publication_date", read_only=True)
    source = serializers.CharField(source="publication.source", read_only=True)
    source_display = serializers.CharField(
        source="publication.get_source_display", read_only=True
    )
    raw_text_preview = serializers.CharField(
        source="publication.text_preview", read_only=True
    )
    publication_metadata = serializers.JSONField(
        source="publication.metadata", read_only=True
    )

    is_overdue = serializers.BooleanField(read_only=True)
    days_until_deadline = serializers.IntegerField(read_only=True)

    class Meta:
        model = JudicialEvent
        fields = [
            "id",
            # Classificação
            "event_type", "event_type_display",
            "status", "status_display",
            "urgency", "urgency_display",
            # Vínculos
            "publication", "publication_id",
            "process", "deadline",
            "assigned_to", "assigned_to_id",
            # Campos derivados da publicação
            "process_cnj", "publication_date",
            "source", "source_display",
            "raw_text_preview", "publication_metadata",
            # Workflow
            "notes", "assigned_at", "resolved_at",
            "is_overdue", "days_until_deadline",
            # Timestamps
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "assigned_at", "resolved_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        # Em serializações sem request (ex.: tasks internas), não liberamos
        # atribuição a ninguém além do próprio usuário (quando disponível).
        qs = self._allowed_users_queryset(request)
        if "assigned_to_id" in self.fields:
            self.fields["assigned_to_id"].queryset = qs

    @staticmethod
    def _allowed_users_queryset(request):
        """Tenta restringir usuários ao escopo do tenant.

        Como este app é plugável, o modelo de membership pode variar.
        A heurística abaixo cobre os padrões mais comuns.
        Se não der para inferir, cai para um fallback seguro (apenas self).
        """
        if not request or not getattr(request, "user", None):
            return User.objects.none()

        org = getattr(request, "organization", None)
        office = getattr(request, "office", None)

        # Fallback seguro: apenas o próprio usuário
        fallback = User.objects.filter(pk=request.user.pk)
        if not org:
            return fallback

        # Tentativas de relacionamentos típicos
        candidates = []
        try:
            candidates.append(User.objects.filter(organization=org))
        except Exception:
            pass
        try:
            candidates.append(User.objects.filter(organizations=org))
        except Exception:
            pass
        try:
            # memberships__organization (com/sem office)
            if office:
                candidates.append(User.objects.filter(memberships__organization=org, memberships__office=office).distinct())
            candidates.append(User.objects.filter(memberships__organization=org).distinct())
        except Exception:
            pass
        try:
            if office:
                candidates.append(User.objects.filter(office=office))
        except Exception:
            pass
        try:
            if office:
                candidates.append(User.objects.filter(offices=office))
        except Exception:
            pass

        # Se alguma query funcionou e não está vazia, usamos.
        for qs in candidates:
            try:
                if qs.exists():
                    return qs
            except Exception:
                continue

        return fallback

    def update(self, instance, validated_data):
        # Quando muda status para "resolved", seta resolved_at
        from django.utils import timezone
        new_status = validated_data.get("status")
        if new_status == "resolved" and instance.status != "resolved":
            validated_data["resolved_at"] = timezone.now()
        # Quando muda assigned_to, seta assigned_at
        new_assigned = validated_data.get("assigned_to")
        if new_assigned and new_assigned != instance.assigned_to:
            validated_data["assigned_at"] = timezone.now()
            if validated_data.get("status") == "new":
                validated_data["status"] = "assigned"
        return super().update(instance, validated_data)

    def validate(self, attrs):
        """Validação extra contra atribuição cross-tenant."""
        request = self.context.get("request")
        assigned = attrs.get("assigned_to")
        if assigned is None:
            return attrs

        allowed = self._allowed_users_queryset(request)
        try:
            if not allowed.filter(pk=assigned.pk).exists():
                raise serializers.ValidationError({
                    "assigned_to_id": "Usuário inválido para este tenant/office.",
                })
        except Exception:
            # Em caso de erro inesperado na heurística, aplica fallback seguro.
            if request and assigned.pk != request.user.pk:
                raise serializers.ValidationError({
                    "assigned_to_id": "Atribuição a outros usuários não está habilitada nesta configuração.",
                })
        return attrs


# ─────────────────────────────────────────────────────────────────────────────
# ProcessMonitoring
# ─────────────────────────────────────────────────────────────────────────────

class ProcessMonitoringSerializer(serializers.ModelSerializer):
    created_by = UserMiniSerializer(read_only=True)
    process_number = serializers.CharField(source="process.number", read_only=True)
    process_title = serializers.SerializerMethodField()
    recent_publications_count = serializers.SerializerMethodField()

    class Meta:
        model = ProcessMonitoring
        fields = [
            "id", "process", "process_number", "process_title",
            "process_cnj", "sources",
            "tribunal", "tribunal_index", "current_phase",
            "is_active", "autocomplete_enabled",
            "initial_sync_done", "last_synced_at", "sync_cursors",
            "created_by", "recent_publications_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "process_cnj", "tribunal", "tribunal_index", "current_phase",
            "initial_sync_done", "last_synced_at", "sync_cursors",
            "created_at", "updated_at",
        ]

    def get_process_title(self, obj):
        try:
            return obj.process.title or obj.process.number
        except Exception:
            return obj.process_cnj

    def get_recent_publications_count(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=30)
        return Publication.objects.filter(
            process_cnj=obj.process_cnj,
            organization=obj.organization,
            office=obj.office,
            created_at__gte=cutoff,
        ).count()

    def create(self, validated_data):
        process = validated_data["process"]
        # Preenche process_cnj automaticamente
        validated_data["process_cnj"] = process.number
        # Detecta tribunal automaticamente
        from apps.publications.services import CNJMatcher
        sigla, index = CNJMatcher.extract_tribunal(process.number)
        if sigla:
            validated_data.setdefault("tribunal", sigla)
            validated_data.setdefault("tribunal_index", index)
        # Default: monitorar todas as fontes disponíveis
        validated_data.setdefault("sources", ["datajud", "comunica"])
        return super().create(validated_data)


# ─────────────────────────────────────────────────────────────────────────────
# PublicationRule
# ─────────────────────────────────────────────────────────────────────────────

class PublicationRuleSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    urgency_display = serializers.CharField(source="get_auto_urgency_display", read_only=True)

    class Meta:
        model = PublicationRule
        fields = [
            "id", "event_type", "event_type_display",
            "description", "base_legal",
            "days", "business_days",
            "auto_create_deadline", "auto_urgency", "urgency_display",
            "is_active", "priority",
            "created_at", "updated_at",
        ]


# ─────────────────────────────────────────────────────────────────────────────
# PublicationFilter
# ─────────────────────────────────────────────────────────────────────────────

class PublicationFilterSerializer(serializers.ModelSerializer):
    filter_type_display = serializers.CharField(source="get_filter_type_display", read_only=True)

    class Meta:
        model = PublicationFilter
        fields = [
            "id", "filter_type", "filter_type_display",
            "value", "description", "process",
            "is_active", "case_sensitive",
            "match_count", "last_matched_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["match_count", "last_matched_at", "created_at", "updated_at"]


# ─────────────────────────────────────────────────────────────────────────────
# PublicationImport
# ─────────────────────────────────────────────────────────────────────────────

class PublicationImportSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    triggered_by = UserMiniSerializer(read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    duration_seconds = serializers.IntegerField(read_only=True)

    class Meta:
        model = PublicationImport
        fields = [
            "id", "source", "source_display", "status", "status_display",
            "reference_date",
            "total_found", "total_imported", "total_duplicates",
            "total_matched", "total_errors",
            "filters_applied", "error_log", "summary",
            "success_rate", "duration_seconds",
            "started_at", "finished_at", "triggered_by",
        ]
        read_only_fields = fields


# ─────────────────────────────────────────────────────────────────────────────
# DataJud lookup (read-only, não salva)
# ─────────────────────────────────────────────────────────────────────────────

class DataJudResultSerializer(serializers.Serializer):
    cnj_number = serializers.CharField()
    tribunal = serializers.CharField()
    tribunal_index = serializers.CharField()
    classe = serializers.CharField()
    assunto = serializers.CharField()
    orgao_julgador = serializers.CharField()
    data_ajuizamento = serializers.CharField()
    fase_atual = serializers.CharField()
    movimentos = serializers.ListField()
    partes = serializers.ListField()
