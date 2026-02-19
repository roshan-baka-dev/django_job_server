from django.contrib import admin
from django.urls import path
from common.views import JobCreateView, JobStatusView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/jobs/create", JobCreateView.as_view(), name="job-create"),
    path("api/jobs/<uuid:job_id>/status", JobStatusView.as_view(), name="job-status"),
]