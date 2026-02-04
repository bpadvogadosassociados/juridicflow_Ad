from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView, MeView, MembershipsView, OfficesView,
    CustomerViewSet, ProcessViewSet, DeadlineViewSet, DocumentViewSet,
    FeeAgreementViewSet, InvoiceViewSet
)

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customers")
router.register(r"processes", ProcessViewSet, basename="processes")
router.register(r"deadlines", DeadlineViewSet, basename="deadlines")
router.register(r"documents", DocumentViewSet, basename="documents")
router.register(r"finance/agreements", FeeAgreementViewSet, basename="agreements")
router.register(r"finance/invoices", InvoiceViewSet, basename="invoices")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/memberships/", MembershipsView.as_view(), name="memberships"),
    path("org/offices/", OfficesView.as_view(), name="org-offices"),
    path("", include(router.urls)),
]
