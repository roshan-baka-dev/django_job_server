from rest_framework import serializers
from django.utils import timezone

SCHEDULE_TYPES = {"immediate", "run_at", "cron", "delay_from_now", "polling"}


class JobCreateSerializer(serializers.Serializer):
    app_name = serializers.CharField(max_length=255)
    user_id = serializers.CharField(max_length=255)
    account_id = serializers.CharField(max_length=255)
    board_id = serializers.CharField(max_length=255, required=False, allow_null=True, default=None)
    task_type = serializers.CharField(max_length=255)
    schedule = serializers.DictField()
    data = serializers.DictField(required=False, default=dict)

    def validate_schedule(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("schedule must be an object")
        stype = value.get("type")
        if stype not in SCHEDULE_TYPES:
            raise serializers.ValidationError(
                f"schedule.type must be one of: {', '.join(sorted(SCHEDULE_TYPES))}"
            )
        if stype == "run_at":
            ts = value.get("timestamp")
            if not ts:
                raise serializers.ValidationError("schedule.timestamp required for type run_at")
            try:
                timezone.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                raise serializers.ValidationError("schedule.timestamp must be a valid ISO 8601 datetime")
        elif stype == "cron":
            if not value.get("expression"):
                raise serializers.ValidationError("schedule.expression required for type cron")
        elif stype == "delay_from_now":
            d = value.get("duration_seconds")
            if d is None:
                raise serializers.ValidationError("schedule.duration_seconds required for type delay_from_now")
            try:
                secs = int(d)
            except (TypeError, ValueError):
                raise serializers.ValidationError("schedule.duration_seconds must be an integer")
            if secs < 0:
                raise serializers.ValidationError("schedule.duration_seconds must be >= 0")
        elif stype == "polling":
            i = value.get("interval_seconds")
            if i is None:
                raise serializers.ValidationError("schedule.interval_seconds required for type polling")
            try:
                secs = int(i)
            except (TypeError, ValueError):
                raise serializers.ValidationError("schedule.interval_seconds must be an integer")
            if secs <= 0:
                raise serializers.ValidationError("schedule.interval_seconds must be > 0")
        return value