"""
Mixin para ViewSets do DRF que injeta o usuário autenticado
na instância do modelo antes de salvar, para que os signals
de ActivityEvent possam capturar o autor da ação.

Uso:
    class ProcessViewSet(ActivityMixin, ScopedModelViewSet):
        ...
"""


class ActivityMixin:
    """
    Injeta request.user e o request na instância salva,
    permitindo que os signals do apps.activity capturem o ator.
    """

    def perform_create(self, serializer):
        instance = serializer.save(
            organization=self.request.organization,
            office=self.request.office,
        )
        # Log manually instead of re-triggering signal
        try:
            from apps.activity.models import log_event
            model_name = instance.__class__.__name__
            label = str(instance)
            log_event(
                module=self._activity_module(),
                action="created",
                summary=f"{self.request.user.get_full_name() or self.request.user.email} criou {model_name} '{label}'",
                actor=self.request.user,
                organization=self.request.organization,
                office=self.request.office,
                entity_type=model_name,
                entity_id=str(instance.pk),
                entity_label=label,
                request=self.request,
            )
        except Exception:
            pass

    def perform_update(self, serializer):
        instance = serializer.save()
        instance._current_user = self.request.user
        instance._current_request = self.request
        # Signal foi disparado pelo save() acima, mas user foi anotado depois.
        # Para garantir, chamamos log_event diretamente aqui:
        try:
            from apps.activity.models import log_event
            model_name = instance.__class__.__name__
            label = str(instance)
            log_event(
                module=self._activity_module(),
                action="updated",
                summary=f"{self.request.user.get_full_name() or self.request.user.email} atualizou {model_name} '{label}'",
                actor=self.request.user,
                organization=self.request.organization,
                office=self.request.office,
                entity_type=model_name,
                entity_id=str(instance.pk),
                entity_label=label,
                request=self.request,
            )
        except Exception:
            pass

    def perform_destroy(self, instance):
        try:
            from apps.activity.models import log_event
            model_name = instance.__class__.__name__
            label = str(instance)
            log_event(
                module=self._activity_module(),
                action="deleted",
                summary=f"{self.request.user.get_full_name() or self.request.user.email} excluiu {model_name} '{label}'",
                actor=self.request.user,
                organization=self.request.organization,
                office=self.request.office,
                entity_type=model_name,
                entity_id=str(instance.pk),
                entity_label=label,
                request=self.request,
            )
        except Exception:
            pass
        instance.delete()

    def _activity_module(self) -> str:
        """Sobrescreva nas subclasses ou deixe detectar pelo app_label."""
        name = self.__class__.__name__.lower()
        mapping = {
            "customerviewset":   "customers",
            "processviewset":    "processes",
            "deadlineviewset":   "deadlines",
            "documentviewset":   "documents",
            "feeagreementviewset": "finance",
            "invoiceviewset":    "finance",
            "paymentviewset":    "finance",
            "expenseviewset":    "finance",
            "proposalviewset":   "finance",
            "taskviewset":       "tasks",
            "kanbancolumnviewset": "kanban",
            "kanbancardviewset": "kanban",
            "calendarentryviewset": "calendar",
        }
        for key, module in mapping.items():
            if key in name:
                return module
        return "system"
