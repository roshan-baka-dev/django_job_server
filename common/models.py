import uuid
from django.db import models


class AppUser(models.Model):
    """app_users: app-scoped user identity."""
    app_name = models.CharField(max_length=255, db_index=True)
    monday_user_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "app_users"
        constraints = [
            models.UniqueConstraint(
                fields=["app_name", "monday_user_id"],
                name="app_users_app_name_monday_user_id_uniq",
            )
        ]


class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    PAUSED_RATE_LIMITED = "paused_rate_limited", "Paused (rate limited)"


class ScheduleType(models.TextChoices):
    IMMEDIATE = "immediate", "Immediate"
    RUN_AT = "run_at", "Run at"
    CRON = "cron", "Cron"
    DELAY_FROM_NOW = "delay_from_now", "Delay from now"
    POLLING = "polling", "Polling"


class Job(models.Model):
    """jobs: main job table with UUID PK."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app_name = models.CharField(max_length=255, db_index=True)
    user = models.ForeignKey(
        "common.AppUser",
        on_delete=models.CASCADE,
        related_name="jobs",
        db_column="user_id",
    )
    account_id = models.CharField(max_length=255, db_index=True)
    board_id = models.CharField(max_length=255, null=True, blank=True)
    task_type = models.CharField(max_length=255)
    status = models.CharField(
        max_length=32,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )
    schedule_type = models.CharField(
        max_length=32,
        choices=ScheduleType.choices,
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    cron_expression = models.CharField(max_length=255, null=True, blank=True)
    polling_interval = models.PositiveIntegerField(null=True, blank=True)  # seconds
    polling_state = models.JSONField(null=True, blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jobs"
        indexes = [
            models.Index(fields=["app_name", "status"], name="jobs_app_status_idx"),
            models.Index(fields=["scheduled_at", "status"], name="jobs_scheduled_status_idx"),
            models.Index(fields=["account_id"], name="jobs_account_id_idx"),
        ]


class JobLogErrorType(models.TextChoices):
    TRANSIENT = "transient", "Transient"
    PERMANENT = "permanent", "Permanent"


class JobLog(models.Model):
    """job_logs: per-job event log."""
    job = models.ForeignKey(
        "common.Job",
        on_delete=models.CASCADE,
        related_name="logs",
        db_column="job_id",
    )
    event_type = models.CharField(max_length=255)
    attempt_number = models.PositiveIntegerField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True, unique=True)
    error_type = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        choices=JobLogErrorType.choices,
    )
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_logs"
        indexes = [
            models.Index(fields=["job", "created_at"], name="job_logs_job_created_idx"),
        ]