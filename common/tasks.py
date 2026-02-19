import logging
from celery import shared_task
from django.utils import timezone
import requests

from common.models import Job, JobLog, JobStatus, ScheduleType, JobLogErrorType
from common.rate_limiter import check_rate_limit
from common.channel_utils import publish_job_update

logger = logging.getLogger(__name__)

try:
    from croniter import croniter
except ImportError:
    croniter = None

CALLBACK_TIMEOUT = 30

@shared_task
def enqueue_due_cron_jobs():
    """
    Beat runs this periodically. Finds cron Jobs that are due (scheduled_at <= now),
    enqueues run_job for each, and advances scheduled_at to the next run.
    """
    now = timezone.now()
    due = Job.objects.filter(
        schedule_type=ScheduleType.CRON,
        status=JobStatus.QUEUED,
        scheduled_at__lte=now,
        cron_expression__isnull=False,
    ).exclude(cron_expression="")
    for job in due:
        run_job.apply_async(args=[str(job.id)])
        if croniter and job.cron_expression:
            try:
                it = croniter(job.cron_expression, now)
                next_run = it.get_next(timezone.datetime)
                next_run = timezone.make_aware(next_run) if timezone.is_naive(next_run) else next_run
                job.scheduled_at = next_run
                job.save(update_fields=["scheduled_at", "updated_at"])
            except Exception as e:
                logger.warning("croniter next run failed for job %s: %s", job.id, e)


@shared_task
def dummy_task():
    return "common.tasks loaded"


@shared_task(bind=True, max_retries=None)
def run_job(self, job_id):
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return
    if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        return

    # Calculate Attempt Number (starts at 0, so add 1)
    attempt_number = self.request.retries + 1
    
    # 1. Start Log Key: Unique per attempt
    start_key = f"{job_id}::started::{attempt_number}"
    
    payload = job.payload or {}
    max_retries = payload.get("max_retries", 3)
    retry_backoff_base = payload.get("retry_backoff_base", 60)

    job.status = JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])
    publish_job_update(str(job.id), status=job.status, log=None)

    # Use get_or_create for Start Log
    JobLog.objects.get_or_create(
        idempotency_key=start_key,
        defaults={
            "job": job,
            "event_type": "execution_started",
            "attempt_number": attempt_number,
        }
    )

    publish_job_update(str(job.id), status=job.status, log={
        "event_type": "execution_started",
        "metadata": None,
        "created_at": timezone.now().isoformat(),
    })

    rate_result = check_rate_limit(job.account_id)
    if not rate_result["allowed"]:
        job.status = JobStatus.PAUSED_RATE_LIMITED
        job.save(update_fields=["status", "updated_at"])
        publish_job_update(str(job.id), status=job.status, log=None)
        
        # Log the pause safely
        JobLog.objects.get_or_create(
            idempotency_key=f"{job_id}::rate_limit::{attempt_number}",
            defaults={
                "job": job,
                "event_type": "rate_limited",
                "attempt_number": attempt_number,
                "metadata": {"wait_seconds": rate_result["retry_after_seconds"]}
            }
        )

        run_job.apply_async(
            args=[str(job.id)],
            countdown=rate_result["retry_after_seconds"],
        )
        return

    callback_url = payload.get("callback_url")

    # Construct the key sent to the external server
    # This remains the same so Node knows it's the same attempt
    external_idempotency_key = f"{job_id}_{attempt_number}"

    try:
        if callback_url:
            body = {
                "idempotency_key": external_idempotency_key,
                "payload": payload,
            }
            if job.schedule_type == ScheduleType.POLLING:
                body["job_id"] = str(job.id)
                body["polling_state"] = job.polling_state or {}
            resp = requests.post(
                callback_url,
                json=body,
                timeout=CALLBACK_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        else:
            resp = None  # no response to parse

        # Stateful polling: parse response, update polling_state, reschedule only if not done
        if job.schedule_type == ScheduleType.POLLING and job.polling_interval and callback_url and resp is not None:
            try:
                result_data = resp.json()
            except Exception:
                result_data = {}
            new_state = result_data.get("polling_state")
            if new_state is not None:
                job.polling_state = new_state
            done = result_data.get("done") is True

            if done:
                job.status = JobStatus.COMPLETED
                job.save(update_fields=["status", "polling_state", "updated_at"])
                completion_key = f"{job_id}::completed::{attempt_number}"
                JobLog.objects.get_or_create(
                    idempotency_key=completion_key,
                    defaults={
                        "job": job,
                        "event_type": "execution_completed",
                        "attempt_number": attempt_number,
                    }
                )
                publish_job_update(
                    str(job.id),
                    status=job.status,
                    log={
                        "event_type": "execution_completed",
                        "metadata": None,
                        "created_at": timezone.now().isoformat(),
                    },
                )
            else:
                job.status = JobStatus.QUEUED
                job.save(update_fields=["status", "polling_state", "updated_at"])
                publish_job_update(str(job.id), status=job.status, log=None)
                run_job.apply_async(
                    args=[str(job.id)],
                    countdown=job.polling_interval,
                )
        else:
            # Non-polling (or no callback): mark completed and handle cron
            job.status = JobStatus.COMPLETED
            job.save(update_fields=["status", "updated_at"])
            completion_key = f"{job_id}::completed::{attempt_number}"
            JobLog.objects.get_or_create(
                idempotency_key=completion_key,
                defaults={
                    "job": job,
                    "event_type": "execution_completed",
                    "attempt_number": attempt_number,
                }
            )
            publish_job_update(
                str(job.id),
                status=job.status,
                log={
                    "event_type": "execution_completed",
                    "metadata": None,
                    "created_at": timezone.now().isoformat(),
                },
            )

            if job.schedule_type == ScheduleType.CRON:
                job.status = JobStatus.QUEUED
                job.save(update_fields=["status", "updated_at"])
                publish_job_update(str(job.id), status=job.status, log=None)

    except requests.RequestException as e:
        _handle_callback_failure(
            self=self,
            job=job,
            attempt_number=attempt_number,
            error=e,
            max_retries=max_retries,
            retry_backoff_base=retry_backoff_base,
        )
    except Exception as e:
        _handle_execution_failure(
            self=self,
            job=job,
            attempt_number=attempt_number,
            error=e,
            max_retries=max_retries,
            retry_backoff_base=retry_backoff_base,
        )


def _is_transient_http_error(exc):
    if not hasattr(exc, "response") or exc.response is None:
        return True
    status = exc.response.status_code
    if status >= 500:
        return True
    if status in (408, 429):
        return True
    return False


def _handle_callback_failure(
    self,
    job,
    attempt_number,
    error,
    max_retries,
    retry_backoff_base,
):
    """
    Handles network/callback failures. 
    Crucially uses get_or_create to prevent UniqueConstraint crashes on retries.
    """
    transient = _is_transient_http_error(error)
    error_type = JobLogErrorType.TRANSIENT if transient else JobLogErrorType.PERMANENT
    status_code = getattr(getattr(error, "response", None), "status_code", None)
    
    # Robust key generation and get_or_create
    idempotency_key = f"{job.id}::failure::{attempt_number}"

    JobLog.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "job": job,
            "event_type": "execution_failed",
            "attempt_number": attempt_number,
            "error_type": error_type,
            "metadata": {"message": str(error), "status_code": status_code},
        }
    )

    publish_job_update(
        str(job.id),
        status=job.status,
        log={
            "event_type": "execution_failed",
            "metadata": None,
            "created_at": timezone.now().isoformat(),
        },
    )

    if transient and attempt_number <= max_retries:
        countdown = retry_backoff_base * (2 ** (attempt_number - 1))
        countdown = min(countdown, 3600)
        # Using raise self.retry is cleaner than calling self.retry
        raise self.retry(countdown=countdown, max_retries=max_retries)
    else:
        job.status = JobStatus.FAILED
        job.save(update_fields=["status", "updated_at"])
        publish_job_update(str(job.id), status=job.status, log=None)


def _handle_execution_failure(
    self,
    job,
    attempt_number,
    error,
    max_retries,
    retry_backoff_base,
):
    """
    Handles internal/generic exceptions.
    """
    #Robust key generation and get_or_create
    idempotency_key = f"{job.id}::exception::{attempt_number}"

    JobLog.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "job": job,
            "event_type": "execution_failed",
            "attempt_number": attempt_number,
            "error_type": JobLogErrorType.TRANSIENT,
            "metadata": {"message": str(error)},
        }
    )

    publish_job_update(
        str(job.id),
        status=job.status,
        log={
            "event_type": "execution_failed",
            "metadata": None,
            "created_at": timezone.now().isoformat(),
        },
    )

    if attempt_number <= max_retries:
        countdown = retry_backoff_base * (2 ** (attempt_number - 1))
        countdown = min(countdown, 3600)
        raise self.retry(countdown=countdown, max_retries=max_retries)
    else:
        job.status = JobStatus.FAILED
        job.save(update_fields=["status", "updated_at"])
        publish_job_update(str(job.id), status=job.status, log=None)