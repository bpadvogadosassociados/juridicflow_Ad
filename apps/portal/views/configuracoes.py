"""
Views de Configurações do Portal.
"""
from django.contrib import messages
from django.shortcuts import render, redirect

from apps.portal.decorators import require_portal_access
from apps.portal.forms import ThemeForm


@require_portal_access()
def settings_view(request):
    if request.method == "POST":
        form = ThemeForm(request.POST)
        if form.is_valid():
            request.session["theme"] = form.cleaned_data["theme"]
            messages.success(request, "Tema atualizado!")
            return redirect("portal:settings")
    else:
        form = ThemeForm(initial={"theme": request.session.get("theme", "default")})

    return render(request, "portal/settings.html", {
        "form": form,
        "active_page": "configuracoes",
    })