import uuid
from django.utils import timezone
from common.models import AppUser, Job, JobStatus, ScheduleType
from common.tasks import run_job

try:
    from croniter import croniter
except ImportError:
    croniter = None


def _ensure_user(app_name, user_id):
    user, _ = AppUser.objects.get_or_create(
        app_name=app_name,
        monday_user_id=user_id,
        defaults={"app_name": app_name, "monday_user_id": user_id},
    )
    return user


def _payload_from_config_and_data(config, payload):
    """Merge config metadata with request data for Job.payload."""
    out = {
        "callback_url": config.get("callback_url"),
        "max_retries": config.get("max_retries"),
        "retry_backoff_base": config.get("retry_backoff_base"),
        "data": payload,
    }
    for k, v in config.items():
        if k not in ("app_name", "user_id", "account_id", "board_id", "task_type"):
            out.setdefault(k, v)
    return out


def run_immediate(config, payload):
    """Creates job, queues Celery task immediately. Returns job UUID."""
    user = _ensure_user(config["app_name"], config["user_id"])
    job = Job.objects.create(
        app_name=config["app_name"],
        user=user,
        account_id=config["account_id"],
        board_id=config.get("board_id"),
        task_type=config["task_type"],
        status=JobStatus.QUEUED,
        schedule_type=ScheduleType.IMMEDIATE,
        payload=_payload_from_config_and_data(config, payload),
    )
    run_job.apply_async(args=[str(job.id)])
    return str(job.id)


def run_at(config, payload, timestamp):
    """Creates job with scheduled_at, queues with Celery eta. Returns job UUID."""
    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp)
    user = _ensure_user(config["app_name"], config["user_id"])
    job = Job.objects.create(
        app_name=config["app_name"],
        user=user,
        account_id=config["account_id"],
        board_id=config.get("board_id"),
        task_type=config["task_type"],
        status=JobStatus.QUEUED,
        schedule_type=ScheduleType.RUN_AT,
        scheduled_at=timestamp,
        payload=_payload_from_config_and_data(config, payload),
    )
    run_job.apply_async(args=[str(job.id)], eta=timestamp)
    return str(job.id)


def run_cron(config, payload, cron_expression):
    """Creates job with cron_expression; Celery Beat task will enqueue when due. Returns job UUID."""
    user = _ensure_user(config["app_name"], config["user_id"])
    scheduled_at = None
    if croniter:
        base = timezone.now()
        it = croniter(cron_expression, base)
        next_run = it.get_next(timezone.datetime)
        scheduled_at = timezone.make_aware(next_run) if timezone.is_naive(next_run) else next_run
    job = Job.objects.create(
        app_name=config["app_name"],
        user=user,
        account_id=config["account_id"],
        board_id=config.get("board_id"),
        task_type=config["task_type"],
        status=JobStatus.QUEUED,
        schedule_type=ScheduleType.CRON,
        cron_expression=cron_expression,
        scheduled_at=scheduled_at,
        payload=_payload_from_config_and_data(config, payload),
    )
    return str(job.id)


def run_after_delay(config, payload, duration_seconds):
    """scheduled_at = now + duration; same as run_at from there. Returns job UUID."""
    run_at_time = timezone.now() + timezone.timedelta(seconds=duration_seconds)
    return run_at(config, payload, run_at_time)


def run_polling(config, payload, interval_seconds):
    """Creates job; task runs and reschedules itself after each run using polling_state. Returns job UUID."""
    user = _ensure_user(config["app_name"], config["user_id"])
    job = Job.objects.create(
        app_name=config["app_name"],
        user=user,
        account_id=config["account_id"],
        board_id=config.get("board_id"),
        task_type=config["task_type"],
        status=JobStatus.QUEUED,
        schedule_type=ScheduleType.POLLING,
        polling_interval=interval_seconds,
        polling_state={},
        payload=_payload_from_config_and_data(config, payload),
    )
    run_job.apply_async(args=[str(job.id)])
    return str(job.id)