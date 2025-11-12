# repairs/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

def job_upload_path(instance, filename):
    return f"jobs/{instance.job_id}/{filename}"

# Fix: define generate_job_id before RepairJob model
def generate_job_id():
    return f"JOB-{uuid.uuid4().hex[:8].upper()}"

class Store(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Customer(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.phone}"

class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Vendor(models.Model):
    name = models.CharField(max_length=200)
    contact = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name

class Courier(models.Model):
    name = models.CharField(max_length=200)
    tracking_url_template = models.URLField(blank=True)

    def __str__(self):
        return self.name

class JobPhoto(models.Model):
    # optional model for storing multiple photos per job
    job = models.ForeignKey('RepairJob', on_delete=models.CASCADE, related_name='photos')
    file = models.FileField(upload_to=job_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class StatusHistory(models.Model):
    job = models.ForeignKey('RepairJob', on_delete=models.CASCADE, related_name='history')
    from_status = models.CharField(max_length=100)
    to_status = models.CharField(max_length=100)
    by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class RepairJob(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('dispatched', 'Dispatched to Warehouse'),
        ('received', 'Received at Warehouse'),
        ('sent_vendor', 'Sent to Vendor'),
        ('repaired', 'Repaired'),
        ('replacement', 'Replacement'),
        ('ready', 'Ready for Pickup'),
        ('closed', 'Closed'),
    ]

    job_id = models.CharField(max_length=50, default=generate_job_id, unique=True)
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    item_name = models.CharField(max_length=200)
    item_details = models.TextField(blank=True)
    damage_reason = models.TextField(blank=True)
    repair_days = models.IntegerField(default=2)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='open')
    courier = models.ForeignKey(Courier, on_delete=models.SET_NULL, null=True, blank=True)
    awb = models.CharField(max_length=200, blank=True)
    otp = models.CharField(max_length=6, blank=True)
    otp_expiry = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def compute_delivery_date(self):
        if self.repair_days is not None:
            return (timezone.now().date() + timezone.timedelta(days=self.repair_days))
        return None

    def save(self, *args, **kwargs):
        if not self.delivery_date:
            self.delivery_date = self.compute_delivery_date()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.job_id

class PendingCreate(models.Model):
    temp_id = models.CharField(max_length=60, unique=True)
    payload = models.JSONField()
    otp = models.CharField(max_length=6)
    otp_expiry = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class OtpLog(models.Model):
    phone = models.CharField(max_length=20)
    event = models.CharField(max_length=50)
    payload = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class NotifyLog(models.Model):
    channel = models.CharField(max_length=20)  # whatsapp/sms/email
    to = models.CharField(max_length=50)
    type = models.CharField(max_length=80)
    payload = models.JSONField(null=True, blank=True)
    result = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    
class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=[
        ('store', 'Store Staff'),
        ('warehouse', 'Warehouse Staff'),
        ('admin', 'Admin'),
    ])
    

def generate_job_id():
    import uuid
    return f"JOB-{uuid.uuid4().hex[:8].upper()}"
