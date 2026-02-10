from django.shortcuts import render, redirect, get_object_or_404


def landing(request):
    if request.user.is_authenticated and not (request.user.is_staff or request.user.is_superuser):
        return redirect("portal:dashboard")
    return render(request, "portal/landing.html")