import json
from channels.generic.websocket import AsyncWebsocketConsumer


class JobStatusConsumer(AsyncWebsocketConsumer):
    """Listens on channel group job_{job_id}; pushes job_update messages to the client."""

    async def connect(self):
        self.job_id = self.scope["url_route"]["kwargs"]["job_id"]
        self.room_group_name = f"job_{self.job_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def job_update(self, event):
        """Called when channel_layer.group_send(..., {'type': 'job_update', ...})."""
        await self.send(text_data=json.dumps({
            "event": "job_update",
            "status": event.get("status"),
            "log": event.get("log"),
        }))