from apps.app_a.handlers import bulk_excel_insert, delayed_archive, scheduled_cron_task, polling_task


HANDLER_REGISTRY = {
    ("app_a", "bulk_excel_insert"): bulk_excel_insert,
    ("app_a", "delayed_archive"): delayed_archive,
    ("app_a", "scheduled_cron_task"): scheduled_cron_task,
    ("app_a", "polling_task"): polling_task,
}


def get_handler(app_name, task_type):
    key = (app_name, task_type)
    handler = HANDLER_REGISTRY.get(key)
    if not handler:
        raise ValueError(f"No handler registered for {key}")
    return handler