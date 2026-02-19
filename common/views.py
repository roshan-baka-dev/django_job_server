from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from common.models import Job, JobLog
from common.serializers import JobCreateSerializer
from common.routing import get_handler


class JobCreateView(APIView):
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = JobCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        try:
            handler = get_handler(data["app_name"], data["task_type"])
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        job_id = handler(data)
        return Response({"id": job_id}, status=status.HTTP_201_CREATED)


class JobStatusView(APIView):
    """GET /api/jobs/{job_id}/status – job row + latest job_logs."""

    def get(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        logs = (
            JobLog.objects.filter(job=job)
            .order_by("-created_at")[:20]
            .values("event_type", "attempt_number", "error_type", "metadata", "created_at")
        )
        from django.utils.dateformat import format as date_format
        created_at = job.created_at.isoformat() if job.created_at else None
        scheduled_at = job.scheduled_at.isoformat() if job.scheduled_at else None
        return Response({
            "job_id": str(job.id),
            "status": job.status,
            "task_type": job.task_type,
            "created_at": created_at,
            "scheduled_at": scheduled_at,
            "logs": list(logs),
        })