from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "enqueue-due-cron-jobs": {
        "task": "common.tasks.enqueue_due_cron_jobs",
        "schedule": crontab(minute="*"),  # every minute
    },
}