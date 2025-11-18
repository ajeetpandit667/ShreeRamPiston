# repairs/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.db.models.functions import TruncWeek
from django.db.models import Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import random, string, uuid, datetime

from .models import (
    Store, Customer, RepairJob, PendingCreate, StatusHistory,
    OtpLog, NotifyLog, Courier, JobPhoto, StaffProfile
)
from .notifications import send_notification
from .models import LoginProfile

from django.http import JsonResponse

# ---------------------------------------
# ml models trained from db 
# -------------------------------------

def api_delay_prediction(request, job_id):
    job = RepairJob.objects.get(job_id=job_id)

    warehouse_load = RepairJob.objects.filter(
        store=job.store, status__in=["received", "repairing"]
    ).count()

    vendor_load = RepairJob.objects.filter(status="sent_vendor").count()

    # Import ML predictor lazily so missing ML dependencies don't break the app
    try:
        from repairs.ml.delay_model import predict_delay
        prediction = predict_delay(
            repair_days=job.repair_days,
            warehouse_load=warehouse_load,
            vendor_load=vendor_load,
            damage_text=job.damage_reason or ""
        )
    except Exception:
        prediction = None

    return JsonResponse({
        "job_id": job_id,
        "delay_chance": prediction
    })


def api_best_warehouse(request):
    """Return a simple recommendation for the best warehouse to route a job to.

    This is a lightweight heuristic endpoint: if there are warehouses it
    returns the first warehouse name and an approximate current load (number
    of jobs in 'received' or 'repairing'). If no warehouses exist it returns
    null/0.
    """
    try:
        from .models import Warehouse
        active_statuses = ["received", "repairing"]
        total_active = RepairJob.objects.filter(status__in=active_statuses).count()
        warehouses = list(Warehouse.objects.all())
        if not warehouses:
            return JsonResponse({"warehouse": None, "load": 0})

        # Simple even distribution estimate: divide active jobs by warehouses
        per = total_active // max(1, len(warehouses))
        # choose the warehouse with the smallest id (stable) as recommendation
        recommended = sorted(warehouses, key=lambda w: (getattr(w, 'id', 0)))[0]

        return JsonResponse({
            "warehouse": recommended.name,
            "load": per
        })
    except Exception:
        return JsonResponse({"warehouse": None, "load": 0})
    
    
# duplicate removed: keep the earlier safe `api_best_warehouse` implementation

# -------------------------------------------------------
# ROLE CHECKING HELPERS
# -------------------------------------------------------

def has_role(role):
    """Decorator factory: ensures user has a specific role."""
    def check(user):
        try:
            return user.is_authenticated and user.staffprofile.role == role
        except:
            return False
    return user_passes_test(check, login_url='/login/')

store_required = has_role("store")
warehouse_required = has_role("warehouse")


# -------------------------------------------------------
# COMMON HELPERS
# -------------------------------------------------------

def generate_otp_code(n=6):
    return ''.join(random.choices(string.digits, k=n))


# -------------------------------------------------------
# DASHBOARD ROUTES
# -------------------------------------------------------

@login_required
def dashboard(request):
    user = request.user

    # Admin goes to admin panel
    if user.is_superuser:
        return redirect('/admin/')

    # Must have staff profile
    try:
        profile = user.staffprofile
    except:
        return HttpResponse("Your role is not assigned. Contact admin.")

    # Role-based redirect
    if profile.role == "store":
        return redirect("repairs:store_dashboard")

    if profile.role == "warehouse":
        return redirect("repairs:warehouse_dashboard")

    return HttpResponse("Invalid role. Contact admin.")


# -------------------------------------------------------
# STORE DASHBOARD
# -------------------------------------------------------

@login_required
@store_required
def store_dashboard(request):
    profile = request.user.staffprofile
    jobs = RepairJob.objects.filter(store=profile.store)

    # Filters
    job_id = request.GET.get("job_id")
    status = request.GET.get("status")
    phone = request.GET.get("phone")

    if job_id:
        jobs = jobs.filter(job_id__icontains=job_id)

    if status:
        jobs = jobs.filter(status=status)

    if phone:
        jobs = jobs.filter(customer__phone__icontains=phone)

    jobs = jobs.order_by("-created_at")
    return render(request, "repairs/store_dashboard.html", {"jobs": jobs})


# -------------------------------------------------------
# WAREHOUSE DASHBOARD
# -------------------------------------------------------

@login_required
@warehouse_required
def warehouse_dashboard(request):

    jobs = RepairJob.objects.filter(
        status__in=["dispatched", "received", "repairing", "ready", "not_repairable", "dispatched_back"]
    )

    # Filters
    job_id = request.GET.get("job_id")
    status = request.GET.get("status")
    phone = request.GET.get("phone")

    if job_id:
        jobs = jobs.filter(job_id__icontains=job_id)

    if status:
        jobs = jobs.filter(status=status)

    if phone:
        jobs = jobs.filter(customer__phone__icontains=phone)

    jobs = jobs.order_by("-updated_at")

    return render(request, "repairs/warehouse_dashboard.html", {"jobs": jobs})


# -------------------------------------------------------
# HOME + JOB LIST + JOB DETAIL
# -------------------------------------------------------

@login_required
def home(request):
    stores = Store.objects.all()
    return render(request, 'repairs/home.html', {'stores': stores})


def job_list(request):
    # Build queryset first, apply filters, then slice
    jobs = RepairJob.objects.order_by("-created_at")

    # Store staff only sees their own jobs
    if request.user.is_authenticated and hasattr(request.user, "staffprofile"):
        try:
            if request.user.staffprofile.role == "store":
                jobs = jobs.filter(store=request.user.staffprofile.store)
        except Exception:
            # If staffprofile access fails, fall back to no additional filter
            pass

    # Allow searching by job_id and phone from the job_list search form
    job_id = request.GET.get("job_id")
    phone = request.GET.get("phone")
    if job_id:
        jobs = jobs.filter(job_id__icontains=job_id)
    if phone:
        jobs = jobs.filter(customer__phone__icontains=phone)

    # Limit to latest 200 after filtering
    jobs = jobs[:200]

    return render(request, "repairs/job_list.html", {"jobs": jobs})


def job_detail(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    return render(request, "repairs/job_detail.html", {"job": job})


# -------------------------------------------------------
# OTP WORKFLOW
# -------------------------------------------------------

@csrf_protect
def request_otp(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST")

    phone = request.POST.get("phone")
    name = request.POST.get("name", "")
    store_id = request.POST.get("store")
    item = request.POST.get("item", "")
    reason = request.POST.get("reason", "")
    repair_days = int(request.POST.get("days", 2))
    email = request.POST.get("email", "").strip()

    if not phone or not store_id:
        return JsonResponse({"success": False, "error": "phone and store required"})

    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return JsonResponse({"success": False, "error": "Store not found"})

    otp = generate_otp_code()
    expiry = timezone.now() + datetime.timedelta(minutes=15)
    temp_id = str(uuid.uuid4())

    payload = {
        "phone": phone,
        "name": name,
        "email": email,
        "store_id": store.id,
        "item": item,
        "reason": reason,
        "repair_days": repair_days
    }

    PendingCreate.objects.create(
        temp_id=temp_id,
        payload=payload,
        otp=otp,
        otp_expiry=expiry
    )

    # Log OTP
    OtpLog.objects.create(
        phone=phone,
        event="request_created",
        payload={"temp_id": temp_id, "otp": otp, "email": email}
    )

    # Send email OTP
    if email:
        try:
            send_mail(
                "Your Repair Request OTP",
                f"Dear {name},\nYour verification OTP is: {otp}\n(Valid for 15 minutes)",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )
        except:
            pass

    if settings.DEBUG:
        print(f"OTP for {phone}: {otp}")

    return JsonResponse({"success": True, "temp_id": temp_id})


@csrf_protect
def verify_otp(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST")

    temp_id = request.POST.get("temp_id")
    otp = request.POST.get("otp")

    if not temp_id or not otp:
        return JsonResponse({"success": False, "error": "Missing fields"})

    try:
        pending = PendingCreate.objects.get(temp_id=temp_id)
    except:
        return JsonResponse({"success": False, "error": "Invalid request"})

    if pending.otp != otp:
        pending.attempts += 1
        pending.save()
        return JsonResponse({"success": False, "error": "Invalid OTP"})

    if pending.otp_expiry < timezone.now():
        pending.delete()
        return JsonResponse({"success": False, "error": "OTP expired"})

    payload = pending.payload
    store = Store.objects.get(id=payload["store_id"])

    customer, _ = Customer.objects.get_or_create(
        phone=payload["phone"],
        defaults={"name": payload["name"], "email": payload["email"]}
    )

    job = RepairJob.objects.create(
        store=store,
        customer=customer,
        item_name=payload["item"],
        damage_reason=payload["reason"],
        repair_days=payload["repair_days"],
    )

    StatusHistory.objects.create(job=job, from_status="created", to_status="open")

    pending.delete()
    return JsonResponse({"success": True, "job_id": job.job_id})


# -------------------------------------------------------
# PICKUP OTP + PHOTO UPLOAD
# -------------------------------------------------------


@login_required
@csrf_protect
def generate_pickup_otp(request, job_id):
    # Generate an OTP for pickup and notify customer
    job = get_object_or_404(RepairJob, job_id=job_id)
    otp = generate_otp_code()
    expiry = timezone.now() + datetime.timedelta(minutes=30)
    job.otp = otp
    job.otp_expiry = expiry
    job.save()

    # send a notification (mock during development)
    try:
        send_notification(job.customer.phone, f"Pickup OTP: {otp}", channel='mock')
    except Exception:
        pass

    if settings.DEBUG:
        return JsonResponse({"success": True, "otp": otp})
    return JsonResponse({"success": True})


@csrf_protect
def verify_pickup(request, job_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST")

    otp = request.POST.get("otp")
    job = get_object_or_404(RepairJob, job_id=job_id)

    if not job.otp or otp != job.otp or (job.otp_expiry and job.otp_expiry < timezone.now()):
        return JsonResponse({"success": False, "error": "Invalid or expired OTP"})

    job.status = "closed"
    job.save()
    try:
        StatusHistory.objects.create(job=job, from_status="ready", to_status="closed", by=request.user if request.user.is_authenticated else None)
    except Exception:
        pass

    return JsonResponse({"success": True})


@login_required
@csrf_protect
def upload_photo(request, job_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST")

    job = get_object_or_404(RepairJob, job_id=job_id)
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({"success": False, "error": "file missing"})

    photo = JobPhoto.objects.create(job=job, file=f)
    return JsonResponse({"success": True, "photo_id": photo.id})


# -------------------------------------------------------
# STATUS TRANSITIONS
# -------------------------------------------------------

@login_required
@store_required
@csrf_protect
def send_to_warehouse(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    job.status = "dispatched"
    job.save()
    return JsonResponse({"success": True})


@login_required
@warehouse_required
@csrf_protect
def mark_received(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    job.status = "received"
    job.save()
    return redirect("repairs:warehouse_dashboard")


@login_required
@warehouse_required
@csrf_protect
def mark_repairing(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    job.status = "repairing"
    job.save()
    return redirect("repairs:warehouse_dashboard")


@login_required
@warehouse_required
@csrf_protect
def mark_ready(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    job.status = "ready"
    job.save()
    return redirect("repairs:warehouse_dashboard")


@login_required
@warehouse_required
@csrf_protect
def mark_not_repairable(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    job.status = "not_repairable"
    job.save()
    return redirect("repairs:warehouse_dashboard")


@login_required
@warehouse_required
@csrf_protect
def dispatch_back_to_store(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    job.status = "dispatched_back"
    job.save()
    return redirect("repairs:warehouse_dashboard")


# -------------------------------------------------------
# CHART DATA
# -------------------------------------------------------

@login_required
def job_stats(request):
    data = (
        RepairJob.objects.annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(count=Count("id"))
        .order_by("week")
    )

    return JsonResponse({
        "weeks": [d["week"].strftime("%d %b") for d in data],
        "counts": [d["count"] for d in data]
    })


def register(request):
    """Handle simple user registration from the login/register template.

    Creates a Django user (username set to email), a LoginProfile, and an
    optional Customer entry if `mobile` is provided. Logs the user in and
    redirects to `dashboard` on success. Renders the login template with an
    `error` context on failure.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        mobile = request.POST.get('mobile', '').strip()

        if not email or not password:
            return render(request, 'registration/login.html', {'error': 'Email and password are required.'})

        if password != confirm:
            return render(request, 'registration/login.html', {'error': 'Passwords do not match.'})

        if User.objects.filter(username=email).exists():
            return render(request, 'registration/login.html', {'error': 'A user with that email already exists.'})

        # create user
        user = User.objects.create_user(username=email, email=email, first_name=name)
        user.set_password(password)
        user.save()

        # create LoginProfile
        try:
            LoginProfile.objects.create(user=user, is_registered=True)
        except Exception:
            pass

        # optionally create Customer record for this mobile
        try:
            if mobile:
                Customer.objects.get_or_create(phone=mobile, defaults={'name': name, 'email': email})
        except Exception:
            pass

        # log the user in
        user = authenticate(username=email, password=password)
        if user:
            auth_login(request, user)
            return redirect('repairs:dashboard')

        return render(request, 'registration/login.html', {'error': 'Registration succeeded but login failed. Please login manually.'})

    # If GET, just render the login/register page
    return render(request, 'registration/login.html')
