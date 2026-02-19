from django.utils import timezone
from common.models import AppUser, Job, ScheduleType
from common.scheduling import (
    schedule_immediate,
    schedule_run_at,
    schedule_cron,
    schedule_delay_from_now,
    schedule_polling,
)

# task_type -> callable(validated_data) that creates Job and calls a scheduling primitive, returns job.id
_handler_registry = {}


def register_handler(task_type):
    def decorator(fn):
        _handler_registry[task_type] = fn
        return fn
    return decorator


def get_handler(task_type):
    return _handler_registry.get(task_type, default_handler)


def default_handler(validated_data):
    """Create job and schedule it from validated request data. Used when no app-specific handler is registered."""
    app_name = validated_data["app_name"]
    user_id = validated_data["user_id"]
    account_id = validated_data["account_id"]
    board_id = validated_data.get("board_id")
    task_type = validated_data["task_type"]
    schedule = validated_data["schedule"]
    data = validated_data.get("data") or {}

    user, _ = AppUser.objects.get_or_create(
        app_name=app_name,
        monday_user_id=user_id,
        defaults={"app_name": app_name, "monday_user_id": user_id},
    )

    stype = schedule["type"]
    schedule_type_map = {
        "immediate": ScheduleType.IMMEDIATE,
        "run_at": ScheduleType.RUN_AT,
        "cron": ScheduleType.CRON,
        "delay_from_now": ScheduleType.DELAY_FROM_NOW,
        "polling": ScheduleType.POLLING,
    }
    schedule_type = schedule_type_map[stype]

    job = Job.objects.create(
        app_name=app_name,
        user=user,
        account_id=account_id,
        board_id=board_id,
        task_type=task_type,
        status=JobStatus.PENDING,
        schedule_type=schedule_type,
        payload=data,
    )

    if stype == "immediate":
        schedule_immediate(job)
    elif stype == "run_at":
        ts = timezone.datetime.fromisoformat(schedule["timestamp"].replace("Z", "+00:00"))
        if timezone.is_naive(ts):
            ts = timezone.make_aware(ts)
        schedule_run_at(job, ts)
    elif stype == "cron":
        schedule_cron(job, schedule["expression"])
    elif stype == "delay_from_now":
        schedule_delay_from_now(job, int(schedule["duration_seconds"]))
    elif stype == "polling":
        schedule_polling(job, int(schedule["interval_seconds"]))

    return str(job.id)