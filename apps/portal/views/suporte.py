"""
Views de Suporte e Chat — CORRIGIDO para os models reais.

Campos reais:
  ChatThread: organization, office, type, title, created_by, created_at
    (SEM: participants M2M, updated_at — usa ChatMember para membros)
  ChatMember: thread, user, joined_at
  ChatMessage: thread, sender (não author), body (não text), created_at
"""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from apps.portal.models import SupportTicket, ChatThread, ChatMember, ChatMessage
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.forms import SupportTicketForm
from apps.portal.views._helpers import parse_json_body, log_activity


# ==================== SUPORTE ====================

@require_portal_access()
@require_http_methods(["GET", "POST"])
def support_new(request):
    if request.method == "POST":
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            SupportTicket.objects.create(
                organization=request.organization,
                office=request.office,
                subject=form.cleaned_data["subject"],
                message=form.cleaned_data["message"],
                target="office_admin",
                created_by=request.user,
            )
            messages.success(request, "Ticket de suporte enviado com sucesso!")
            return redirect("portal:support_inbox")
        else:
            messages.error(request, "Preencha todos os campos obrigatórios.")
    else:
        form = SupportTicketForm()

    return render(request, "portal/support_new.html", {
        "form": form,
        "active_page": "suporte",
    })


@require_portal_access()
def support_inbox(request):
    tickets = SupportTicket.objects.filter(
        organization=request.organization,
        office=request.office,
    ).order_by("-created_at")

    return render(request, "portal/support_inbox.html", {
        "tickets": tickets,
        "active_page": "suporte",
    })


# ==================== CHAT ====================

@require_portal_json()
def chat_threads(request):
    # Busca threads onde o user é membro via ChatMember
    member_thread_ids = ChatMember.objects.filter(
        user=request.user
    ).values_list("thread_id", flat=True)

    threads = ChatThread.objects.filter(
        organization=request.organization,
        office=request.office,
        id__in=member_thread_ids,
    ).order_by("-created_at")

    data = []
    for thread in threads:
        last_msg = thread.messages.order_by("-created_at").first()
        data.append({
            "id": thread.id,
            "title": thread.title or "",
            "type": thread.type,
            "last_message": last_msg.body[:100] if last_msg else "",
            "last_message_at": last_msg.created_at.isoformat() if last_msg else None,
        })

    return JsonResponse({"threads": data})


@require_portal_json()
@require_http_methods(["POST"])
def chat_thread_create(request):
    payload = parse_json_body(request)
    title = payload.get("title", "").strip()
    thread_type = payload.get("type", "direct")
    participant_ids = payload.get("participant_ids", [])

    thread = ChatThread.objects.create(
        organization=request.organization,
        office=request.office,
        type=thread_type,
        title=title,
        created_by=request.user,
    )

    # Adiciona o criador como membro
    ChatMember.objects.create(thread=thread, user=request.user)

    # Adiciona outros participantes
    if participant_ids:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for user in User.objects.filter(id__in=participant_ids):
            ChatMember.objects.get_or_create(thread=thread, user=user)

    return JsonResponse({"ok": True, "thread_id": thread.id})


@require_portal_json()
def chat_messages(request, thread_id):
    # Valida que user é membro da thread
    is_member = ChatMember.objects.filter(
        thread_id=thread_id, user=request.user
    ).exists()

    if not is_member:
        return JsonResponse({"error": "Não é membro desta conversa"}, status=403)

    thread = ChatThread.objects.filter(
        id=thread_id,
        organization=request.organization,
        office=request.office,
    ).first()
    if not thread:
        return JsonResponse({"error": "Thread não encontrada"}, status=404)

    msgs = thread.messages.select_related("sender").order_by("created_at")[:100]
    data = [
        {
            "id": m.id,
            "body": m.body,
            "sender": m.sender.get_full_name() or m.sender.email if m.sender else "Sistema",
            "sender_id": m.sender_id,
            "created_at": m.created_at.isoformat(),
            "is_mine": m.sender_id == request.user.id,
        }
        for m in msgs
    ]

    return JsonResponse({"messages": data})


@require_portal_json()
@require_http_methods(["POST"])
def chat_send(request, thread_id):
    # Valida que user é membro
    is_member = ChatMember.objects.filter(
        thread_id=thread_id, user=request.user
    ).exists()
    if not is_member:
        return JsonResponse({"error": "Não é membro desta conversa"}, status=403)

    thread = ChatThread.objects.filter(
        id=thread_id,
        organization=request.organization,
        office=request.office,
    ).first()
    if not thread:
        return JsonResponse({"error": "Thread não encontrada"}, status=404)

    payload = parse_json_body(request)
    body = payload.get("body", "").strip()
    if not body:
        return JsonResponse({"error": "Mensagem vazia"}, status=400)

    msg = ChatMessage.objects.create(
        thread=thread,
        sender=request.user,
        body=body,
    )

    return JsonResponse({
        "ok": True,
        "message": {
            "id": msg.id,
            "body": msg.body,
            "sender": request.user.get_full_name() or request.user.email,
            "created_at": msg.created_at.isoformat(),
        },
    })