"""
Views de Suporte e Chat.
"""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from apps.portal.models import SupportTicket, ChatThread, ChatMember, ChatMessage
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.forms import SupportTicketForm
from apps.portal.views._helpers import parse_json_body, log_activity

User = get_user_model()


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
        # Unread count for this user in this thread
        unread = 0  # placeholder — add read-tracking if needed
        data.append({
            "id": thread.id,
            "title": thread.title or "Conversa",
            "type": thread.type,
            "last_message": last_msg.body[:80] if last_msg else "",
            "last_message_at": last_msg.created_at.isoformat() if last_msg else None,
            "unread": unread,
        })

    return JsonResponse({"items": data})


@require_portal_json()
@require_http_methods(["POST"])
def chat_thread_create(request):
    payload = parse_json_body(request)
    title = payload.get("title", "").strip()
    thread_type = payload.get("type", "group")
    participant_ids = payload.get("participant_ids", [])
    emails = payload.get("emails", [])

    if not title:
        return JsonResponse({"error": "Título obrigatório"}, status=400)

    thread = ChatThread.objects.create(
        organization=request.organization,
        office=request.office,
        type=thread_type,
        title=title,
        created_by=request.user,
    )

    # Adiciona criador
    ChatMember.objects.create(thread=thread, user=request.user)

    # Participantes por IDs
    if participant_ids:
        for user in User.objects.filter(id__in=participant_ids):
            ChatMember.objects.get_or_create(thread=thread, user=user)

    # Participantes por emails (mesmo office)
    if emails:
        from apps.memberships.models import Membership
        office_user_ids = Membership.objects.filter(
            office=request.office,
            organization=request.organization,
            is_active=True,
        ).values_list("user_id", flat=True)

        email_list = [e.strip() for e in emails if e.strip()]
        for user in User.objects.filter(
            email__in=email_list, id__in=office_user_ids
        ):
            ChatMember.objects.get_or_create(thread=thread, user=user)

    return JsonResponse({
        "ok": True,
        "thread": {
            "id": thread.id,
            "title": thread.title,
            "type": thread.type,
        }
    })


@require_portal_json()
def chat_messages(request, thread_id):
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

    return JsonResponse({"items": data, "thread_title": thread.title or "Conversa"})


@require_portal_json()
@require_http_methods(["POST"])
def chat_send(request, thread_id):
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
            "is_mine": True,
        },
    })


@require_portal_json()
def chat_users_search(request):
    """Autocomplete de usuários do office para o modal de nova conversa."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"items": []})

    from apps.memberships.models import Membership
    from django.db.models import Q as DQ
    office_user_ids = Membership.objects.filter(
        office=request.office,
        organization=request.organization,
        is_active=True,
    ).values_list("user_id", flat=True)

    users = User.objects.filter(
        id__in=office_user_ids
    ).filter(
        DQ(email__icontains=q) | DQ(first_name__icontains=q) | DQ(last_name__icontains=q)
    ).exclude(id=request.user.id)[:10]

    return JsonResponse({
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.get_full_name() or u.email,
            }
            for u in users
        ]
    })
