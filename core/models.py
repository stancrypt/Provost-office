from django.db import models
from django.utils import timezone

class UploadedResult(models.Model):
    result_id = models.CharField(max_length=50, unique=True)
    file = models.FileField(upload_to='results/')
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.result_id
    
class AttendanceResult(models.Model):
    month_id = models.CharField(max_length=10, unique=True)
    report_data = models.JSONField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

