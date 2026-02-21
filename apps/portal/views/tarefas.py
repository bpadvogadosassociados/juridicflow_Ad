"""
Views de Kanban / Tarefas — CORRIGIDO para os models reais.

Campos reais:
  KanbanColumn: board, title, order (não position/color)
  KanbanCard: board, column, number, title, body_md, order, created_by, created_at
"""
from django.db.models import Max, F
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.portal.models import KanbanBoard, KanbanColumn, KanbanCard
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.views._helpers import parse_json_body, log_activity

from apps.portal.permissions import require_role, require_action
from apps.portal.audit import audited

# ==================== HTML ====================

@require_portal_access()
def kanban(request):
    org = request.organization
    office = request.office
    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    columns = board.columns.prefetch_related("cards").order_by("order")

    return render(request, "portal/kanban.html", {
        "board": board,
        "columns": columns,
        "active_page": "tarefas",
    })


@require_portal_access()
def task_list(request):
    qs = KanbanCard.objects.filter(
        board__organization=request.organization,
        board__office=request.office,
    ).select_related("column").order_by("-created_at")

    # Anotar campos que o template espera
    qs = qs.annotate(
        column_name=F("column__title"),
    )

    # Filtros
    search = request.GET.get("search", "").strip()
    status_f = request.GET.get("status", "").strip()

    if search:
        qs = qs.filter(title__icontains=search)
    # status_f: o template mostra status_choices, mas KanbanCard
    # não tem "status" — o status vem da coluna.
    # Se existir lógica de mapping column → status, aplicar aqui.

    # Paginação
    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Adicionar _status como property nos objetos
    # (não dá pra anotar com Annotate porque é lógica de negócio)
    COLUMN_STATUS_MAP = {
    "a fazer": "todo", "to do": "todo", "todo": "todo",
    "em andamento": "in_progress", "doing": "in_progress",
    "revisão": "review", "review": "review",
    "concluído": "done", "done": "done", "finalizado": "done",
    "backlog": "backlog",
}

    for card in page_obj:
        col_title = (card.column.title or "").lower().strip()
        card.status = COLUMN_STATUS_MAP.get(col_title, "todo")

    status_choices = [
        ("todo", "A fazer"),
        ("doing", "Em andamento"),
        ("blocked", "Bloqueada"),
        ("done", "Concluída"),
    ]

    return render(request, "portal/tasks_list.html", {
        "tasks": page_obj,          # Page object
        "search": search,
        "status_f": status_f,
        "status_choices": status_choices,
        "active_page": "tarefas",
    })


# ==================== BOARD JSON ====================

@require_portal_json()
def kanban_board_json(request):
    org = request.organization
    office = request.office
    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    columns = board.columns.prefetch_related("cards").order_by("order")

    data = []
    for col in columns:
        cards = []
        for card in col.cards.order_by("order"):
            cards.append({
                "id": card.id,
                "number": card.number,
                "title": card.title,
                "body_md": card.body_md or "",
                "order": card.order,
                "created_at": card.created_at.isoformat(),
            })
        data.append({
            "id": col.id,
            "title": col.title,
            "order": col.order,
            "cards": cards,
        })

    return JsonResponse({"board_id": board.id, "columns": data})


# ==================== COLUMNS ====================

@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def kanban_column_create(request):
    org = request.organization
    office = request.office
    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    payload = parse_json_body(request)
    title = payload.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Título obrigatório"}, status=400)

    max_order = board.columns.aggregate(m=Max("order"))["m"] or 0
    col = KanbanColumn.objects.create(
        board=board,
        title=title,
        order=max_order + 1,
    )
    return JsonResponse({
        "ok": True,
        "column": {"id": col.id, "title": col.title, "order": col.order},
    })


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def kanban_column_update(request, column_id):
    col = get_object_or_404(
        KanbanColumn,
        id=column_id,
        board__organization=request.organization,
        board__office=request.office,
    )
    payload = parse_json_body(request)
    if "title" in payload:
        col.title = payload["title"].strip()
    if "order" in payload:
        col.order = int(payload["order"])
    col.save()
    return JsonResponse({"ok": True})


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def kanban_column_delete(request, column_id):
    col = get_object_or_404(
        KanbanColumn,
        id=column_id,
        board__organization=request.organization,
        board__office=request.office,
    )
    col.cards.all().delete()
    col.delete()
    return JsonResponse({"ok": True})


# ==================== CARDS ====================

@require_portal_json()
@require_role("assistant")
@require_http_methods(["POST"])
def kanban_card_create(request):
    org = request.organization
    office = request.office
    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    payload = parse_json_body(request)

    column_id = payload.get("column_id")
    if not column_id:
        return JsonResponse({"error": "column_id obrigatório"}, status=400)

    column = get_object_or_404(KanbanColumn, id=column_id, board=board)

    title = payload.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Título obrigatório"}, status=400)

    # Auto-increment number
    max_number = board.cards.aggregate(m=Max("number"))["m"] or 0
    max_order = column.cards.aggregate(m=Max("order"))["m"] or 0

    card = KanbanCard.objects.create(
        board=board,
        column=column,
        number=max_number + 1,
        title=title,
        body_md=payload.get("body_md", "").strip(),
        order=max_order + 1,
        created_by=request.user,
    )
    log_activity(request, "task_create", f"Tarefa #{card.number}: {card.title}")

    return JsonResponse({
        "ok": True,
        "card": {
            "id": card.id,
            "number": card.number,
            "title": card.title,
            "column_id": column.id,
            "order": card.order,
        },
    })


@require_portal_json()
@require_role("assistant")
@require_http_methods(["POST"])
def kanban_card_update(request, card_id):
    card = get_object_or_404(
        KanbanCard,
        id=card_id,
        board__organization=request.organization,
        board__office=request.office,
    )
    payload = parse_json_body(request)
    if "title" in payload:
        card.title = payload["title"].strip()
    if "body_md" in payload:
        card.body_md = payload["body_md"].strip()
    if "order" in payload:
        card.order = int(payload["order"])
    card.save()
    return JsonResponse({"ok": True})


@require_portal_json()
@require_role("assistant")
@require_http_methods(["POST"])
def kanban_card_move(request):
    payload = parse_json_body(request)
    card_id = payload.get("id") or payload.get("card_id")
    if not card_id:
        return JsonResponse({"error": "card_id obrigatório"}, status=400)
    card = get_object_or_404(
        KanbanCard, id=card_id,
        board__organization=request.organization,
        board__office=request.office,
    )
    target_column_id = payload.get("to_column_id") or payload.get("column_id")
    if not target_column_id:
        return JsonResponse({"error": "column_id obrigatório"}, status=400)
    target_column = get_object_or_404(
        KanbanColumn, id=target_column_id,
        board__organization=request.organization,
        board__office=request.office,
    )
    card.column = target_column
    if "order" in payload:
        card.order = int(payload["order"])
    card.save()
    return JsonResponse({"ok": True})


@require_portal_json()
def kanban_card_detail(request, card_id):
    card = get_object_or_404(
        KanbanCard,
        id=card_id,
        board__organization=request.organization,
        board__office=request.office,
    )
    return JsonResponse({
        "id": card.id,
        "number": card.number,
        "title": card.title,
        "body_md": card.body_md or "",
        "column_id": card.column_id,
        "order": card.order,
        "created_at": card.created_at.isoformat(),
    })