
"""Views de autenticação e seleção de contexto."""
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.memberships.models import Membership
from apps.offices.models import Office
from apps.portal.forms import PortalLoginForm
from apps.portal.decorators import require_portal_access


def landing(request):
    if request.user.is_authenticated and not (request.user.is_staff or request.user.is_superuser):
        return redirect('portal:dashboard')
    return render(request, 'portal/landing.html')


@require_http_methods(['GET', 'POST'])
def portal_login(request):
    if request.user.is_authenticated:
        return redirect('portal:dashboard')
    form = PortalLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.cleaned_data['user']
        login(request, user)
        return redirect('portal:dashboard')
    return render(request, 'portal/login.html', {'form': form})


@login_required
def portal_logout(request):
    logout(request)
    return redirect('portal:login')


@require_portal_access(check_office=False)
def set_office(request, office_id: int):
    org = request.organization
    office = get_object_or_404(Office, id=office_id, organization=org, is_active=True)
    has_membership = Membership.objects.filter(user=request.user, organization=org, office=office, is_active=True).exists()
    if not has_membership:
        return HttpResponseForbidden('Você não possui vínculo ativo neste escritório.')
    request.session['office_id'] = office.id
    return redirect('portal:dashboard')
