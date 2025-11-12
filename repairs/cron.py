from django.utils import timezone
from datetime import timedelta
from .models import RepairJob
from .notifications import send_notification

def send_reminders():
    tomorrow = timezone.now().date() + timedelta(days=2)
    jobs = RepairJob.objects.filter(delivery_date=tomorrow, status__in=['open','dispatched','received'])
    for job in jobs:
        send_notification(job.customer.phone, f"Reminder: Your repair {job.job_id} will be ready soon.")
