from rest_framework import serializers
from .models import ActivityEvent


class ActivityEventSerializer(serializers.ModelSerializer):
    actor_display = serializers.SerializerMethodField()
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    module_display = serializers.CharField(source="get_module_display", read_only=True)

    class Meta:
        model = ActivityEvent
        fields = [
            "id", "created_at",
            "actor", "actor_name", "actor_display",
            "module", "module_display",
            "action", "action_display",
            "entity_type", "entity_id", "entity_label",
            "summary",
            "changes",
            "ip_address",
        ]

    def get_actor_display(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.email
        return obj.actor_name or "Sistema"
