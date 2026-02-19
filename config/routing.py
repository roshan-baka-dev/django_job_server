from django.urls import path
from common.consumers import JobStatusConsumer

websocket_urlpatterns = [
    path("ws/jobs/<uuid:job_id>/", JobStatusConsumer.as_asgi()),
]