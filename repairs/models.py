# repairs/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()


# Upload Path for Job Photos
def job_upload_path(instance, filename):
    return f"jobs/{instance.job.job_id}/{filename}"


# Generate Job ID
def generate_job_id():
    return f"JOB-{uuid.uuid4().hex[:8].upper()}"


# ============================
# Store / Customer / Warehouse
# ============================

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


# ============================
# Repair Job Model
# ============================

class RepairJob(models.Model):

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('dispatched', 'Dispatched to Warehouse'),
        ('received', 'Received at Warehouse'),
        ('repairing', 'Repairing'),
        ('not_repairable', 'Not Repairable'),
        ('ready', 'Ready for Pickup'),
        ('dispatched_back', 'Dispatched Back to Store'),
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
        if self.repair_days:
            return timezone.now().date() + timedelta(days=self.repair_days)
        return None

    def save(self, *args, **kwargs):
        if not self.delivery_date:
            self.delivery_date = self.compute_delivery_date()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.job_id


# ============================
# Photos / History
# ============================

class JobPhoto(models.Model):
    job = models.ForeignKey(RepairJob, on_delete=models.CASCADE, related_name='photos')
    file = models.FileField(upload_to=job_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class StatusHistory(models.Model):
    job = models.ForeignKey(RepairJob, on_delete=models.CASCADE, related_name='history')
    from_status = models.CharField(max_length=100)
    to_status = models.CharField(max_length=100)
    by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)


# ============================
# OTP / Notifications
# ============================

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
    channel = models.CharField(max_length=20)   # sms/email/whatsapp/mock
    to = models.CharField(max_length=50)
    type = models.CharField(max_length=80)
    payload = models.JSONField(null=True, blank=True)
    result = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)


# ============================
# Staff / Login Profiles
# ============================

class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ('store', 'Store Staff'),
        ('warehouse', 'Warehouse Staff'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.SET_NULL)
    warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class LoginProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='loginprofile')
    is_registered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"LoginProfile({self.user.username}) registered={self.is_registered}"
