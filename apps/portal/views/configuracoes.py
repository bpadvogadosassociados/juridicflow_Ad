"""
Views de Configurações do Portal.
"""
from django.contrib import messages
from django.shortcuts import render, redirect

from apps.portal.decorators import require_portal_access
from apps.portal.forms import ThemeForm

from apps.shared.permissions import require_role, require_action
from apps.portal.audit import audited

from apps.portal.models import OfficePreference

@require_portal_access()
@require_role("manager")
def settings_view(request):
    pref, _ = OfficePreference.objects.get_or_create(office=request.office)
    tab = request.GET.get("tab", "appearance")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "theme":
            theme = request.POST.get("theme", "default")
            pref.theme = theme
            pref.save(update_fields=["theme", "updated_at"])
            messages.success(request, "Tema atualizado!")
            return redirect("portal:settings")

    return render(request, "portal/settings.html", {
        "active_page": "settings",
        "tab": tab,
        "theme": pref.theme or "default",
    })