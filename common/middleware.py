import os
from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class InternalApiSecretMiddleware(MiddlewareMixin):
    """Reject requests to /api/ if X-Internal-Secret header is missing or wrong. 401."""

    def process_request(self, request):
        if not request.path.startswith("/api/"):
            return None
        secret = getattr(settings, "INTERNAL_API_SECRET", None) or os.environ.get("INTERNAL_API_SECRET", "")
        if not secret:
            return None  # no secret configured: allow (e.g. dev)
        provided = request.headers.get("X-Internal-Secret", "")
        if provided != secret:
            return HttpResponse("Unauthorized", status=401)
        return None