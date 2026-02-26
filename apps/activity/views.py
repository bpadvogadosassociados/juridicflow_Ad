"""
Endpoints REST para o módulo Atividade (Audit Log).

GET /api/activity/            — listar eventos (paginado, filtros)
GET /api/activity/summary/    — métricas agregadas para Equipe
GET /api/activity/export/     — exportar CSV
GET /api/activity/<id>/       — detalhe de um evento
"""

import csv
from datetime import datetime, timedelta

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.api.permissions import IsInTenant
from .models import ActivityEvent
from .serializers import ActivityEventSerializer


class ActivityPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class ActivityListView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request):
        if not getattr(request, "office", None):
            return Response({"detail": "X-Office-Id obrigatório."}, status=400)

        qs = ActivityEvent.objects.filter(
            organization=request.organization,
            office=request.office,
        ).select_related("actor")

        # ── Filtros ────────────────────────────────────────────────────
        module = request.query_params.get("module")
        if module:
            qs = qs.filter(module=module)

        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        actor_id = request.query_params.get("actor")
        if actor_id:
            qs = qs.filter(actor_id=actor_id)

        entity_type = request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)

        entity_id = request.query_params.get("entity_id")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)

        # Período
        period = request.query_params.get("period", "7d")
        date_from = request.query_params.get("date_from")
        date_to   = request.query_params.get("date_to")

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        elif period:
            days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
            days = days_map.get(period)
            if days:
                qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=days))

        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        # Busca textual
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(summary__icontains=search)

        paginator = ActivityPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ActivityEventSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ActivityDetailView(APIView):
    permission_classes = [IsInTenant]

    def get(self, request, event_id):
        try:
            event = ActivityEvent.objects.get(
                id=event_id,
                organization=request.organization,
            )
        except ActivityEvent.DoesNotExist:
            return Response({"detail": "Evento não encontrado."}, status=404)
        return Response(ActivityEventSerializer(event).data)


class ActivitySummaryView(APIView):
    """
    Métricas agregadas para a aba Equipe.
    Retorna contagens por módulo, por ação e top atores.
    """
    permission_classes = [IsInTenant]

    def get(self, request):
        if not getattr(request, "office", None):
            return Response({"detail": "X-Office-Id obrigatório."}, status=400)

        period = request.query_params.get("period", "30d")
        days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)
        since = timezone.now() - timedelta(days=days)

        qs = ActivityEvent.objects.filter(
            organization=request.organization,
            office=request.office,
            created_at__gte=since,
        ).select_related("actor")

        # Total
        total = qs.count()

        # Por módulo
        from django.db.models import Count
        by_module = list(
            qs.values("module")
               .annotate(count=Count("id"))
               .order_by("-count")
        )

        # Por ação
        by_action = list(
            qs.values("action")
               .annotate(count=Count("id"))
               .order_by("-count")
        )

        # Top atores (top 10)
        top_actors = list(
            qs.exclude(actor=None)
               .values("actor__id", "actor_name", "actor__email")
               .annotate(count=Count("id"))
               .order_by("-count")[:10]
        )

        # Série diária (últimos N dias)
        from django.db.models.functions import TruncDate
        daily = list(
            qs.annotate(day=TruncDate("created_at"))
               .values("day")
               .annotate(count=Count("id"))
               .order_by("day")
        )

        # Throughput de tarefas: concluídas vs criadas
        tasks_created   = qs.filter(module="tasks",  action="created").count()
        tasks_completed = qs.filter(module="tasks",  action="completed").count()
        deadlines_ok    = qs.filter(module="deadlines", action="completed").count()
        deadlines_miss  = qs.filter(module="deadlines", action="status_changed", summary__icontains="vencido").count()

        return Response({
            "period": period,
            "total": total,
            "by_module": by_module,
            "by_action": by_action,
            "top_actors": [
                {
                    "id":    a["actor__id"],
                    "name":  a["actor_name"] or a["actor__email"],
                    "count": a["count"],
                }
                for a in top_actors
            ],
            "daily": [
                {"date": str(d["day"]), "count": d["count"]}
                for d in daily
            ],
            "tasks": {
                "created": tasks_created,
                "completed": tasks_completed,
            },
            "deadlines": {
                "completed_on_time": deadlines_ok,
                "missed": deadlines_miss,
            },
        })


class Echo:
    """Objeto para StreamingHttpResponse do CSV."""
    def write(self, value):
        return value


class ActivityExportView(APIView):
    """Exporta log como CSV (respeita os mesmos filtros do list)."""
    permission_classes = [IsInTenant]

    def get(self, request):
        if not getattr(request, "office", None):
            return Response({"detail": "X-Office-Id obrigatório."}, status=400)

        qs = ActivityEvent.objects.filter(
            organization=request.organization,
            office=request.office,
        ).select_related("actor").order_by("-created_at")

        # Aplicar mesmos filtros do list
        module = request.query_params.get("module")
        if module:
            qs = qs.filter(module=module)
        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)
        period = request.query_params.get("period", "30d")
        days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=days))

        # Log o próprio export
        from apps.activity.models import log_event
        log_event(
            module="system",
            action="exported",
            summary=f"{request.user.get_full_name() or request.user.email} exportou log de atividade",
            actor=request.user,
            organization=request.organization,
            office=request.office,
            request=request,
        )

        def rows():
            yield ["Data/Hora", "Ator", "Módulo", "Ação", "Entidade", "ID", "Resumo", "IP"]
            for e in qs.iterator(chunk_size=500):
                yield [
                    e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    e.actor_name or (e.actor.email if e.actor else ""),
                    e.get_module_display(),
                    e.get_action_display(),
                    e.entity_type,
                    e.entity_id,
                    e.summary,
                    e.ip_address or "",
                ]

        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse(
            (writer.writerow(row) for row in rows()),
            content_type="text/csv",
        )
        filename = f"atividade_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
