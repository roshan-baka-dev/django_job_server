def publish_job_update(job_id, status=None, log=None):
    """Send job_update to channel group job_{job_id} so WebSocket clients get it."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        group_name = f"job_{job_id}"
        message = {"type": "job_update", "status": status, "log": log}
        async_to_sync(channel_layer.group_send)(group_name, message)
    except Exception:
        pass  # channel layer not configured or Redis down