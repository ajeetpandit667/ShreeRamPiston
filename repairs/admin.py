# repairs/admin.py
from django.contrib import admin
from .models import (
	Store, Customer, Warehouse, Vendor, Courier, RepairJob,
	PendingCreate, StatusHistory, JobPhoto, OtpLog, NotifyLog,
	StaffProfile
)


admin.site.register(Store)
admin.site.register(Customer)
admin.site.register(Warehouse)
admin.site.register(Vendor)
admin.site.register(Courier)
admin.site.register(RepairJob)
admin.site.register(PendingCreate)
admin.site.register(StatusHistory)
admin.site.register(JobPhoto)
admin.site.register(OtpLog)
admin.site.register(NotifyLog)
admin.site.register(StaffProfile)
from .models import LoginProfile

admin.site.register(LoginProfile)
