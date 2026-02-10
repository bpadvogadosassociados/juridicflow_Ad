"""
Views de Kanban / Tarefas.
"""
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.portal.models import KanbanBoard, KanbanColumn, KanbanCard
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.views._helpers import parse_json_body, log_activity


# ==================== HTML ====================

@require_portal_access()
def kanban(request):
    org = request.organization
    office = request.office
    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    columns = board.columns.prefetch_related("cards").order_by("position")

    return render(request, "portal/kanban.html", {
        "board": board,
        "columns": columns,
        "active_page": "tarefas",
    })


@require_portal_access()
def task_list(request):
    """Vista em lista das tarefas (cards)."""
    org = request.organization
    office = request.office
    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    cards = KanbanCard.objects.filter(
        board=board,
    ).select_related("column").order_by("column__position", "position")

    return render(request, "portal/task_list.html", {
        "cards": cards,
        "active_page": "tarefas",
    })


# ==================== BOARD JSON ====================

@require_portal_json()
def kanban_board_json(request):
    org = request.organization
    office = request.office
    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    columns = board.columns.prefetch_related("cards").order_by("position")

    data = []
    for col in columns:
        cards = []
        for card in col.cards.order_by("position"):
            cards.append({
                "id": card.id,
                "title": card.title,
                "description": card.description or "",
                "position": card.position,
                "color": card.color or "",
                "created_at": card.created_at.isoformat(),
            })
        data.append({
            "id": col.id,
            "title": col.title,
            "position": col.position,
            "color": col.color or "",
            "cards": cards,
        })

    return JsonResponse({"board_id": board.id, "columns": data})


# ==================== COLUMNS ====================

@require_portal_json()
@require_http_methods(["POST"])
def kanban_column_create(request):
    org = request.organization
    office = request.office
    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    payload = parse_json_body(request)
    title = payload.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Título obrigatório"}, status=400)

    max_pos = board.columns.count()
    col = KanbanColumn.objects.create(
        board=board,
        title=title,
        position=max_pos,
        color=payload.get("color", ""),
    )
    return JsonResponse({
        "ok": True,
        "column": {"id": col.id, "title": col.title, "position": col.position},
    })


@require_portal_json()
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
    if "position" in payload:
        col.position = int(payload["position"])
    if "color" in payload:
        col.color = payload["color"]
    col.save()
    return JsonResponse({"ok": True})


@require_portal_json()
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
@require_http_methods(["POST"])
def kanban_card_create(request):
    org = request.organization
    office = request.office
    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    payload = parse_json_body(request)

    column_id = payload.get("column_id")
    if not column_id:
        return JsonResponse({"error": "column_id obrigatório"}, status=400)

    column = get_object_or_404(
        KanbanColumn,
        id=column_id,
        board=board,
    )
    title = payload.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Título obrigatório"}, status=400)

    max_pos = column.cards.count()
    card = KanbanCard.objects.create(
        board=board,
        column=column,
        title=title,
        description=payload.get("description", "").strip(),
        position=max_pos,
        color=payload.get("color", ""),
    )
    log_activity(request, "task_create", f"Tarefa criada: {card.title}")

    return JsonResponse({
        "ok": True,
        "card": {
            "id": card.id,
            "title": card.title,
            "column_id": column.id,
            "position": card.position,
        },
    })


@require_portal_json()
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
    if "description" in payload:
        card.description = payload["description"].strip()
    if "color" in payload:
        card.color = payload["color"]
    if "position" in payload:
        card.position = int(payload["position"])
    card.save()
    return JsonResponse({"ok": True})


@require_portal_json()
@require_http_methods(["POST"])
def kanban_card_move(request, card_id):
    card = get_object_or_404(
        KanbanCard,
        id=card_id,
        board__organization=request.organization,
        board__office=request.office,
    )
    payload = parse_json_body(request)
    target_column_id = payload.get("column_id")
    if not target_column_id:
        return JsonResponse({"error": "column_id obrigatório"}, status=400)

    target_column = get_object_or_404(
        KanbanColumn,
        id=target_column_id,
        board__organization=request.organization,
        board__office=request.office,
    )
    card.column = target_column
    if "position" in payload:
        card.position = int(payload["position"])
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
        "title": card.title,
        "description": card.description or "",
        "column_id": card.column_id,
        "position": card.position,
        "color": card.color or "",
        "created_at": card.created_at.isoformat(),
    })