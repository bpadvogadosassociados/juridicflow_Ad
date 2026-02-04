from django.db import models

class OrganizationScopedManager(models.Manager):
    def for_request(self, request):
        org = getattr(request, "organization", None)
        office = getattr(request, "office", None)
        if not org:
            return self.none()
        qs = self.get_queryset().filter(organization=org)
        if office:
            qs = qs.filter(office=office)
        return qs
