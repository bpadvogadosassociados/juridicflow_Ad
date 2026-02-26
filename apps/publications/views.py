"""
PUBLICATIONS / ANDAMENTOS — Views DRF
======================================

Endpoints disponíveis:

  Andamentos (feed unificado)
    GET  /api/publications/feed/               → lista JudicialEvents com filtros ricos
    GET  /api/publications/feed/<id>/          → detalhe + marca como "assigned" automaticamente
    PATCH /api/publications/feed/<id>/         → atualizar status, responsável, notas
    POST /api/publications/feed/mark-all-read/ → marca todos como "assigned"

  Publicações brutas
    GET  /api/publications/raw/                → lista Publications (paginada)
    POST /api/publications/raw/                → criar publicação manual
    GET  /api/publications/raw/<id>/           → detalhe

  Monitoramento
    GET  /api/publications/monitoring/         → lista monitoramentos do office
    POST /api/publications/monitoring/         → ativar monitoramento de processo
    GET  /api/publications/monitoring/<id>/    → detalhe
    PATCH /api/publications/monitoring/<id>/   → pausar/ativar/configurar
    DELETE /api/publications/monitoring/<id>/  → remover monitoramento

  Sync
    POST /api/publications/monitoring/<id>/sync/   → forçar sync de um processo
    POST /api/publications/sync-comunica/           → forçar sync do caderno diário

  Importações (log)
    GET  /api/publications/imports/            → histórico de importações

  Regras de prazo
    GET/POST /api/publications/rules/          → CRUD de regras
    PATCH/DELETE /api/publications/rules/<id>/

  Filtros de matching
    GET/POST /api/publications/filters/        → CRUD de filtros
    PATCH/DELETE /api/publications/filters/<id>/

  DataJud lookup
    GET  /api/publications/datajud/?number=... → consulta sem salvar
"""

from datetime import date
from rest_framework import status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

try:
    from apps.api.permissions import IsInTenant, HasMembershipViewPerms
except ImportError:
    from rest_framework.permissions import IsAuthenticated as IsInTenant
    HasMembershipViewPerms = IsAuthenticated

from .models import (
    Publication, JudicialEvent, ProcessMonitoring,
    PublicationRule, PublicationFilter, PublicationImport,
)
from .serializers import (
    PublicationSerializer, PublicationCreateSerializer,
    JudicialEventSerializer,
    ProcessMonitoringSerializer,
    PublicationRuleSerializer,
    PublicationFilterSerializer,
    PublicationImportSerializer,
    DataJudResultSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# Base mixin multi-tenant
# ─────────────────────────────────────────────────────────────────────────────

class PublicationsScopedMixin:
    permission_classes = [IsInTenant]

    def get_org_office(self):
        return self.request.organization, self.request.office

    def scoped_qs(self, model):
        org, office = self.get_org_office()
        return model.objects.filter(organization=org, office=office)

    def save_scoped(self, serializer):
        org, office = self.get_org_office()
        serializer.save(
            organization=org,
            office=office,
            created_by=self.request.user if hasattr(serializer.Meta.model, "created_by_id") else None,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Feed de Andamentos — JudicialEvents (visão principal)
# ─────────────────────────────────────────────────────────────────────────────

class JudicialEventFeedView(APIView):
    """
    Feed principal do módulo Andamentos.
    Lista JudicialEvents com filtros ricos + paginação por cursor.
    """
    permission_classes = [IsInTenant]

    def get(self, request):
        org, office = request.organization, request.office
        qs = JudicialEvent.objects.filter(
            organization=org, office=office,
        ).select_related("publication", "process", "deadline", "assigned_to")

        # ── Filtros ──────────────────────────────────────────────────────────
        source = request.query_params.get("source")
        if source:
            qs = qs.filter(publication__source=source)

        event_type = request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        urgency = request.query_params.get("urgency")
        if urgency:
            qs = qs.filter(urgency=urgency)

        process_id = request.query_params.get("process")
        if process_id:
            qs = qs.filter(process_id=process_id)

        cnj = request.query_params.get("cnj")
        if cnj:
            qs = qs.filter(publication__process_cnj__icontains=cnj)

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)

        unread = request.query_params.get("unread")
        if unread == "true":
            qs = qs.filter(status="new")

        date_from = request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(publication__publication_date__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(publication__publication_date__lte=date_to)

        q = request.query_params.get("q")
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(publication__raw_text__icontains=q) |
                Q(publication__process_cnj__icontains=q) |
                Q(notes__icontains=q)
            )

        qs = qs.order_by("-publication__publication_date", "-created_at")

        # ── Paginação simples ─────────────────────────────────────────────
        page_size = int(request.query_params.get("page_size", 30))
        page = int(request.query_params.get("page", 1))
        total = qs.count()
        start = (page - 1) * page_size
        events = qs[start : start + page_size]

        # ── Sumário / KPIs ─────────────────────────────────────────────────
        all_qs = JudicialEvent.objects.filter(organization=org, office=office)
        today = timezone.now().date()
        summary = {
            "total": all_qs.count(),
            "new": all_qs.filter(status="new").count(),
            "critical": all_qs.filter(urgency="critical", status__in=["new", "assigned", "in_progress"]).count(),
            "urgent": all_qs.filter(urgency="urgent", status__in=["new", "assigned", "in_progress"]).count(),
            "overdue": all_qs.filter(
                deadline__due_date__lt=today,
                status__in=["new", "assigned", "in_progress"],
            ).count(),
            "monitored_processes": ProcessMonitoring.objects.filter(
                organization=org, office=office, is_active=True
            ).count(),
        }

        return Response({
            "results": JudicialEventSerializer(events, many=True).data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (start + page_size) < total,
            "summary": summary,
        })


class JudicialEventDetailView(APIView):
    permission_classes = [IsInTenant]

    def _get_event(self, request, pk):
        org, office = request.organization, request.office
        try:
            return JudicialEvent.objects.select_related(
                "publication", "process", "deadline", "assigned_to"
            ).get(pk=pk, organization=org, office=office)
        except JudicialEvent.DoesNotExist:
            return None

    def get(self, request, pk):
        event = self._get_event(request, pk)
        if not event:
            return Response({"detail": "Não encontrado."}, status=404)
        # Marca como lido (assigned) automaticamente ao abrir
        if event.status == "new":
            event.status = "assigned"
            event.assigned_at = timezone.now()
            event.save(update_fields=["status", "assigned_at"])
        return Response(JudicialEventSerializer(event).data)

    def patch(self, request, pk):
        event = self._get_event(request, pk)
        if not event:
            return Response({"detail": "Não encontrado."}, status=404)
        serializer = JudicialEventSerializer(
            event,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class JudicialEventMarkAllReadView(APIView):
    permission_classes = [IsInTenant]

    def post(self, request):
        org, office = request.organization, request.office
        updated = JudicialEvent.objects.filter(
            organization=org, office=office, status="new"
        ).update(status="assigned", assigned_at=timezone.now())
        return Response({"marked": updated})


# ─────────────────────────────────────────────────────────────────────────────
# Publicações brutas
# ─────────────────────────────────────────────────────────────────────────────

class PublicationListCreateView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        org, office = request.organization, request.office
        qs = Publication.objects.filter(
            organization=org, office=office
        ).select_related("process", "imported_by").order_by("-publication_date", "-import_date")

        # Filtros
        source = request.query_params.get("source")
        if source:
            qs = qs.filter(source=source)

        cnj = request.query_params.get("cnj")
        if cnj:
            qs = qs.filter(process_cnj__icontains=cnj)

        process_id = request.query_params.get("process")
        if process_id:
            qs = qs.filter(process_id=process_id)

        date_from = request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(publication_date__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(publication_date__lte=date_to)

        page_size = int(request.query_params.get("page_size", 30))
        page = int(request.query_params.get("page", 1))
        total = qs.count()
        start = (page - 1) * page_size

        return Response({
            "results": PublicationSerializer(qs[start:start + page_size], many=True).data,
            "total": total,
            "page": page,
            "has_more": (start + page_size) < total,
        })

    def post(self, request):
        """Criação manual de publicação."""
        org, office = request.organization, request.office
        serializer = PublicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .services import PublicationProcessor
        pub_dict = {
            "source": serializer.validated_data.get("source", "manual"),
            "source_id": serializer.validated_data.get("source_id", ""),
            "raw_text": serializer.validated_data["raw_text"],
            "publication_date": str(serializer.validated_data["publication_date"]),
            "process_cnj": serializer.validated_data.get("process_cnj", ""),
            "metadata": serializer.validated_data.get("metadata", {}),
        }

        pub, event, created = PublicationProcessor.process_dict(
            pub_dict, org, office, request.user
        )

        if not created:
            return Response(
                {"detail": "Publicação duplicada (já existe com o mesmo conteúdo).", "id": pub.id},
                status=status.HTTP_200_OK,
            )

        return Response(PublicationSerializer(pub).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# Monitoramento
# ─────────────────────────────────────────────────────────────────────────────

class ProcessMonitoringListCreateView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        org, office = request.organization, request.office
        qs = ProcessMonitoring.objects.filter(
            organization=org, office=office
        ).select_related("process", "created_by").order_by("-created_at")

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active == "true")

        return Response(ProcessMonitoringSerializer(qs, many=True).data)

    def post(self, request):
        org, office = request.organization, request.office

        # Checa se já existe
        process_id = request.data.get("process")
        if process_id and ProcessMonitoring.objects.filter(
            organization=org, office=office, process_id=process_id
        ).exists():
            monitoring = ProcessMonitoring.objects.get(
                organization=org, office=office, process_id=process_id
            )
            monitoring.is_active = True
            monitoring.save(update_fields=["is_active"])
            return Response(ProcessMonitoringSerializer(monitoring).data, status=200)

        serializer = ProcessMonitoringSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            organization=org,
            office=office,
            created_by=request.user,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProcessMonitoringDetailView(APIView):
    permission_classes = [IsInTenant]

    def _get(self, request, pk):
        org, office = request.organization, request.office
        try:
            return ProcessMonitoring.objects.get(pk=pk, organization=org, office=office)
        except ProcessMonitoring.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(request, pk)
        if not obj:
            return Response({"detail": "Não encontrado."}, status=404)
        return Response(ProcessMonitoringSerializer(obj).data)

    def patch(self, request, pk):
        obj = self._get(request, pk)
        if not obj:
            return Response({"detail": "Não encontrado."}, status=404)
        serializer = ProcessMonitoringSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get(request, pk)
        if not obj:
            return Response({"detail": "Não encontrado."}, status=404)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProcessSyncView(APIView):
    """
    Força sincronização de um processo monitorado via DataJud.
    POST /api/publications/monitoring/<pk>/sync/
    """
    permission_classes = [IsInTenant]

    def post(self, request, pk):
        org, office = request.organization, request.office
        try:
            monitoring = ProcessMonitoring.objects.get(pk=pk, organization=org, office=office)
        except ProcessMonitoring.DoesNotExist:
            return Response({"detail": "Monitoramento não encontrado."}, status=404)

        if not monitoring.is_active:
            return Response({"detail": "Monitoramento está pausado."}, status=400)

        from .services import SyncService
        stats = SyncService.sync_process_datajud(monitoring, user=request.user)

        return Response({
            "message": "Sincronização concluída.",
            "cnj": monitoring.process_cnj,
            **stats,
        })


class ComunicaSyncView(APIView):
    """
    Força sync do caderno diário da Comunica API.
    POST /api/publications/sync-comunica/
    body: { "date": "YYYY-MM-DD" }  (opcional)
    """
    permission_classes = [IsInTenant]

    def post(self, request):
        org, office = request.organization, request.office
        raw_date = request.data.get("date")
        target_date = None
        if raw_date:
            try:
                from datetime import datetime
                target_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                return Response({"detail": "Formato de data inválido. Use YYYY-MM-DD."}, status=400)

        from .services import SyncService
        stats = SyncService.sync_comunica_daily(
            org, office, target_date=target_date, user=request.user
        )
        return Response({"message": "Sync Comunica concluído.", **stats})


# ─────────────────────────────────────────────────────────────────────────────
# DataJud lookup (apenas consulta, não salva)
# ─────────────────────────────────────────────────────────────────────────────

class DataJudLookupView(APIView):
    """
    Consulta o DataJud sem salvar nada.
    Usado para preview antes de ativar monitoramento.
    GET /api/publications/datajud/?number=NNNNNNN-DD.AAAA.J.TT.OOOO
    """
    permission_classes = [IsInTenant]

    def get(self, request):
        number = request.query_params.get("number", "").strip()
        if not number:
            return Response({"detail": "Parâmetro 'number' é obrigatório."}, status=400)

        from django.core.cache import cache
        from .services import (
            CNJMatcher,
            DataJudProvider,
            DataJudAuthError,
            DataJudRateLimitError,
            DataJudUpstreamError,
        )

        digits = CNJMatcher.normalize(number)
        if len(digits) != 20:
            return Response(
                {"detail": "CNJ inválido: esperado 20 dígitos.", "number": number},
                status=400,
            )

        tribunal_index = request.query_params.get("tribunal_index", "").strip().lower() or ""
        if tribunal_index:
            # Segurança: impede path injection / índices bizarros.
            import re
            if not re.match(r"^[a-z0-9_]+$", tribunal_index):
                return Response({"detail": "tribunal_index inválido."}, status=400)
        else:
            _, tribunal_index = CNJMatcher.extract_tribunal(number)

        if not tribunal_index:
            return Response(
                {
                    "detail": "Não foi possível detectar o tribunal pelo número CNJ.",
                    "number": number,
                    "hint": "Você pode informar manualmente ?tribunal_index=tjsp (ou cnj, trf3, etc).",
                },
                status=400,
            )

        cache_key = f"datajud:{tribunal_index}:{digits}"
        cached = cache.get(cache_key)
        if cached:
            return Response({"found": True, **cached, "cached": True})

        provider = DataJudProvider()
        try:
            result = provider.search_process(number, tribunal_index)
        except DataJudAuthError as e:
            return Response(
                {
                    "found": False,
                    "number": number,
                    "tribunal": tribunal_index.upper(),
                    "detail": str(e),
                    "hint": "Configure DATAJUD_API_KEY no ambiente/settings.",
                },
                status=502,
            )
        except DataJudRateLimitError as e:
            return Response(
                {
                    "found": False,
                    "number": number,
                    "tribunal": tribunal_index.upper(),
                    "detail": str(e),
                },
                status=503,
            )
        except DataJudUpstreamError as e:
            return Response(
                {
                    "found": False,
                    "number": number,
                    "tribunal": tribunal_index.upper(),
                    "detail": str(e),
                },
                status=502,
            )
        except ValueError as e:
            return Response({"detail": str(e), "number": number}, status=400)

        if not result:
            return Response(
                {
                    "found": False,
                    "number": CNJMatcher.format(digits),
                    "tribunal": tribunal_index.upper(),
                    "detail": "Processo não encontrado no DataJud.",
                },
                status=404,
            )

        cache.set(cache_key, result, 60)  # TTL curto: bom para debug sem martelar API
        return Response({"found": True, **result})


# ─────────────────────────────────────────────────────────────────────────────
# Regras de Prazo
# ─────────────────────────────────────────────────────────────────────────────

class PublicationRuleListCreateView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        org, office = request.organization, request.office
        qs = PublicationRule.objects.filter(
            organization=org, office=office
        ).order_by("-priority", "event_type")
        return Response(PublicationRuleSerializer(qs, many=True).data)

    def post(self, request):
        org, office = request.organization, request.office
        s = PublicationRuleSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(organization=org, office=office)
        return Response(s.data, status=status.HTTP_201_CREATED)


class PublicationRuleDetailView(APIView):
    permission_classes = [IsInTenant]

    def _get(self, request, pk):
        org, office = request.organization, request.office
        try:
            return PublicationRule.objects.get(pk=pk, organization=org, office=office)
        except PublicationRule.DoesNotExist:
            return None

    def patch(self, request, pk):
        obj = self._get(request, pk)
        if not obj:
            return Response({"detail": "Não encontrado."}, status=404)
        s = PublicationRuleSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def delete(self, request, pk):
        obj = self._get(request, pk)
        if not obj:
            return Response({"detail": "Não encontrado."}, status=404)
        obj.delete()
        return Response(status=204)


# ─────────────────────────────────────────────────────────────────────────────
# Filtros de matching
# ─────────────────────────────────────────────────────────────────────────────

class PublicationFilterListCreateView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        org, office = request.organization, request.office
        qs = PublicationFilter.objects.filter(
            organization=org, office=office
        ).order_by("filter_type", "value")
        return Response(PublicationFilterSerializer(qs, many=True).data)

    def post(self, request):
        org, office = request.organization, request.office
        s = PublicationFilterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(organization=org, office=office)
        return Response(s.data, status=status.HTTP_201_CREATED)


class PublicationFilterDetailView(APIView):
    permission_classes = [IsInTenant]

    def _get(self, request, pk):
        org, office = request.organization, request.office
        try:
            return PublicationFilter.objects.get(pk=pk, organization=org, office=office)
        except PublicationFilter.DoesNotExist:
            return None

    def patch(self, request, pk):
        obj = self._get(request, pk)
        if not obj:
            return Response({"detail": "Não encontrado."}, status=404)
        s = PublicationFilterSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def delete(self, request, pk):
        obj = self._get(request, pk)
        if not obj:
            return Response({"detail": "Não encontrado."}, status=404)
        obj.delete()
        return Response(status=204)


# ─────────────────────────────────────────────────────────────────────────────
# Importações (log read-only)
# ─────────────────────────────────────────────────────────────────────────────

class PublicationImportListView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        org, office = request.organization, request.office
        qs = PublicationImport.objects.filter(
            organization=org, office=office
        ).select_related("triggered_by").order_by("-started_at")

        source = request.query_params.get("source")
        if source:
            qs = qs.filter(source=source)

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        limit = int(request.query_params.get("limit", 50))
        return Response(PublicationImportSerializer(qs[:limit], many=True).data)
