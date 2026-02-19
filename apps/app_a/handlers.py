from django.utils import timezone
from common.scheduling import run_immediate, run_at, run_after_delay, run_cron, run_polling

# --- CONFIGURATION ---
# Use localhost for testing. In production, this would be env variable.
NODE_SERVER_URL = "http://127.0.0.1:3000" 

def bulk_excel_insert(data):
    config = {
        "app_name": data["app_name"],
        "user_id": data["user_id"],
        "account_id": data["account_id"],
        "board_id": data.get("board_id"),
        "task_type": "bulk_excel_insert",
        "callback_url": f"{NODE_SERVER_URL}/internal/jobs/bulk_excel_insert",
        "max_retries": 3,
        "retry_backoff_base": 60,
    }
    return run_immediate(config, data.get("data") or {})


def delayed_archive(data):
    config = {
        "app_name": data["app_name"],
        "user_id": data["user_id"],
        "account_id": data["account_id"],
        "board_id": data.get("board_id"),
        "task_type": "delayed_archive",
        "callback_url": f"{NODE_SERVER_URL}/internal/jobs/delayed_archive",
        "max_retries": 2,
        "retry_backoff_base": 120,
    }
    schedule = data.get("schedule") or {}
    stype = schedule.get("type")
    payload = data.get("data") or {}

    if stype == "run_at" and schedule.get("timestamp"):
        ts = timezone.datetime.fromisoformat(schedule["timestamp"].replace("Z", "+00:00"))
        if timezone.is_naive(ts):
            ts = timezone.make_aware(ts)
        return run_at(config, payload, ts)
        
    if stype == "delay_from_now" and schedule.get("duration_seconds") is not None:
        return run_after_delay(config, payload, int(schedule["duration_seconds"]))
        
    return run_immediate(config, payload)

def scheduled_cron_task(data):
    """Handler for recurring work scheduled via cron. Expects schedule.type == 'cron' and schedule.expression."""
    config = {
        "app_name": data["app_name"],
        "user_id": data["user_id"],
        "account_id": data["account_id"],
        "board_id": data.get("board_id"),
        "task_type": "scheduled_cron_task",  # or your task_type
        "callback_url": f"{NODE_SERVER_URL}/internal/jobs/scheduled_cron_task",
        "max_retries": 2,
        "retry_backoff_base": 120,
    }
    schedule = data.get("schedule") or {}
    if schedule.get("type") != "cron" or not schedule.get("expression"):
        return run_immediate(config, data.get("data") or {})
    return run_cron(config, data.get("data") or {}, schedule["expression"])

def polling_task(data):
    """Handler for jobs that run repeatedly at a fixed interval. Expects schedule.type == 'polling' and schedule.interval_seconds."""
    config = {
        "app_name": data["app_name"],
        "user_id": data["user_id"],
        "account_id": data["account_id"],
        "board_id": data.get("board_id"),
        "task_type": "polling_task",
        "callback_url": f"{NODE_SERVER_URL}/internal/jobs/polling_task",
        "max_retries": 2,
        "retry_backoff_base": 120,
    }
    schedule = data.get("schedule") or {}
    if schedule.get("type") != "polling" or schedule.get("interval_seconds") is None:
        return run_immediate(config, data.get("data") or {})
    return run_polling(config, data.get("data") or {}, int(schedule["interval_seconds"]))