"""
Views de Suporte e Chat.
"""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from apps.portal.models import SupportTicket, ChatThread, ChatMessage
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
    threads = ChatThread.objects.filter(
        organization=request.organization,
        office=request.office,
        participants=request.user,
    ).order_by("-updated_at")

    data = []
    for thread in threads:
        last_msg = thread.messages.order_by("-created_at").first()
        data.append({
            "id": thread.id,
            "title": thread.title or "",
            "last_message": last_msg.text[:100] if last_msg else "",
            "last_message_at": last_msg.created_at.isoformat() if last_msg else None,
            "unread": thread.messages.exclude(read_by=request.user).count(),
        })

    return JsonResponse({"threads": data})


@require_portal_json()
@require_http_methods(["POST"])
def chat_thread_create(request):
    payload = parse_json_body(request)
    title = payload.get("title", "").strip()
    participant_ids = payload.get("participant_ids", [])

    thread = ChatThread.objects.create(
        organization=request.organization,
        office=request.office,
        title=title,
        created_by=request.user,
    )
    thread.participants.add(request.user)

    if participant_ids:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(id__in=participant_ids)
        thread.participants.add(*users)

    return JsonResponse({"ok": True, "thread_id": thread.id})


@require_portal_json()
def chat_messages(request, thread_id):
    # Valida que user participa da thread
    thread = ChatThread.objects.filter(
        id=thread_id,
        organization=request.organization,
        office=request.office,
        participants=request.user,
    ).first()
    if not thread:
        return JsonResponse({"error": "Thread não encontrada"}, status=404)

    msgs = thread.messages.select_related("author").order_by("created_at")[:100]
    data = [
        {
            "id": m.id,
            "text": m.text,
            "author": m.author.get_full_name() or m.author.email,
            "author_id": m.author_id,
            "created_at": m.created_at.isoformat(),
            "is_mine": m.author_id == request.user.id,
        }
        for m in msgs
    ]

    # Marca como lido
    thread.messages.exclude(read_by=request.user).update()  # Simplified
    # TODO: M2M read tracking when model supports it

    return JsonResponse({"messages": data})


@require_portal_json()
@require_http_methods(["POST"])
def chat_send(request, thread_id):
    thread = ChatThread.objects.filter(
        id=thread_id,
        organization=request.organization,
        office=request.office,
        participants=request.user,
    ).first()
    if not thread:
        return JsonResponse({"error": "Thread não encontrada"}, status=404)

    payload = parse_json_body(request)
    text = payload.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "Mensagem vazia"}, status=400)

    msg = ChatMessage.objects.create(
        thread=thread,
        author=request.user,
        text=text,
    )
    thread.save(update_fields=["updated_at"])  # Bump timestamp

    return JsonResponse({
        "ok": True,
        "message": {
            "id": msg.id,
            "text": msg.text,
            "author": request.user.get_full_name() or request.user.email,
            "created_at": msg.created_at.isoformat(),
        },
    })