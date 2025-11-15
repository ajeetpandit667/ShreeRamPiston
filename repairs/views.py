# repairs/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from .models import (
    Store, Customer, RepairJob, PendingCreate, StatusHistory, 
    OtpLog, NotifyLog, Courier, JobPhoto
)
from .decorators import store_only
from django.utils import timezone
import random, string, uuid, datetime
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from .notifications import send_notification
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import StaffProfile, RepairJob




def has_role(role):
    def check(user):
        try:
            return user.is_authenticated and hasattr(user, 'staffprofile') and user.staffprofile.role == role
        except StaffProfile.DoesNotExist:
            return False
    return user_passes_test(check)

store_required = has_role('store')
warehouse_required = has_role('warehouse')



@login_required
@store_required
def store_dashboard(request):
    # store-specific page
    profile = request.user.staffprofile
    # only jobs for this store
    jobs = RepairJob.objects.filter(store=profile.store).order_by('-created_at')
    return render(request, 'repairs/store_dashboard.html', {'jobs': jobs})

@login_required
@warehouse_required
def warehouse_dashboard(request):
    profile = request.user.staffprofile
    # jobs that are dispatched/received for warehouse view
    jobs = RepairJob.objects.filter(status__in=['dispatched','received']).order_by('-updated_at')
    return render(request, 'repairs/warehouse_dashboard.html', {'jobs': jobs})


def generate_otp_code(n=6):
    return ''.join(random.choices(string.digits, k=n))

@login_required
def home(request):
    stores = Store.objects.all()
    return render(request, 'repairs/home.html', {'stores': stores})

def job_list(request):
    """
    Show recent jobs. Store staff see only jobs for their store.
    Other users (or anonymous) see all recent jobs.
    """
    jobs = RepairJob.objects.order_by('-created_at')[:200]

    # If the user is authenticated and a store staff member, filter by their store
    if request.user.is_authenticated and hasattr(request.user, 'staffprofile') and request.user.staffprofile.role == 'store':
        jobs = jobs.filter(store=request.user.staffprofile.store)

    return render(request, 'repairs/job_list.html', {'jobs': jobs})
def job_detail(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    return render(request, 'repairs/job_detail.html', {'job': job})

@csrf_protect
def request_otp(request):
    # Expects POST form data: phone, name, store, item, reason, days
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST")

    phone = request.POST.get('phone')
    name = request.POST.get('name', '')
    store_id = request.POST.get('store')
    item = request.POST.get('item', '')
    reason = request.POST.get('reason', '')
    repair_days = int(request.POST.get('days', 2))

    if not phone or not store_id:
        return JsonResponse({'success': False, 'error': 'phone and store required'})

    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Store not found'})

    otp = generate_otp_code()
    expiry = timezone.now() + datetime.timedelta(minutes=15)
    temp_id = str(uuid.uuid4())
    email = request.POST.get('email', '').strip()

    payload = {
        'phone': phone,
        'name': name,
        'email': email,
        'store_id': store.id,
        'item': item,
        'reason': reason,
        'repair_days': repair_days
    }

    PendingCreate.objects.create(
        temp_id=temp_id,
        payload=payload,
        otp=otp,
        otp_expiry=expiry
    )

    # log and mock send
    OtpLog.objects.create(phone=phone, event='request_created', payload={'temp_id': temp_id, 'otp': otp, 'email': email})
    NotifyLog.objects.create(channel='mock', to=phone, type='otp_sent', payload={'otp': otp})
    # send OTP to email if provided
    if email:
        NotifyLog.objects.create(channel='email', to=email, type='otp_sent', payload={'otp': otp})
        # send actual email using Django's send_mail (falls back to console backend in dev)
        try:
            subject = "Your Repair Request OTP"
            message = f"Dear {name},\n\nYour OTP for repair request verification is: {otp}\n\nThis OTP will expire in 15 minutes.\n\nThank you!"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        except Exception:
            # fallback to notify helper if send_mail fails
            try:
                send_notification(email, f'Your OTP is: {otp}', channel='email', payload={'temp_id': temp_id})
            except Exception:
                pass

    if getattr(settings, 'DEBUG', False):
        print(f"[MOCK SMS] OTP for {phone}: {otp}")  # developer convenience
        if email:
            print(f"[MOCK EMAIL] OTP for {email}: {otp}")

    return JsonResponse({'success': True, 'temp_id': temp_id})

@csrf_protect
def verify_otp(request):
    # expects POST: temp_id, otp
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST")

    temp_id = request.POST.get('temp_id')
    otp = request.POST.get('otp')

    if not temp_id or not otp:
        return JsonResponse({'success': False, 'error': 'temp_id and otp required'})

    try:
        pending = PendingCreate.objects.get(temp_id=temp_id)
    except PendingCreate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid request'})

    if pending.otp != otp:
        pending.attempts += 1
        pending.save()
        return JsonResponse({'success': False, 'error': 'Invalid OTP'})

    if pending.otp_expiry < timezone.now():
        pending.delete()
        return JsonResponse({'success': False, 'error': 'OTP expired'})

    payload = pending.payload
    store = Store.objects.get(id=payload['store_id'])
    customer, _ = Customer.objects.get_or_create(
        phone=payload['phone'],
        defaults={'name': payload.get('name', ''), 'email': payload.get('email', '')}
    )

    job = RepairJob.objects.create(
        store=store,
        customer=customer,
        item_name=payload.get('item', ''),
        item_details='',
        damage_reason=payload.get('reason', ''),
        repair_days=payload.get('repair_days', 2),
    )

    StatusHistory.objects.create(job=job, from_status='created', to_status='open', note='Created via OTP flow')
    OtpLog.objects.create(phone=customer.phone, event='verified_create', payload={'job_id': job.job_id})

    # Notify via phone and email if available
    NotifyLog.objects.create(channel='mock', to=customer.phone, type='job_created', payload={'job_id': job.job_id, 'delivery_date': str(job.delivery_date)})
    try:
        send_notification(customer.phone, f"Your job {job.job_id} has been created.", channel='sms', payload={'job_id': job.job_id})
    except Exception:
        pass
    if getattr(customer, 'email', ''):
        NotifyLog.objects.create(channel='email', to=customer.email, type='job_created', payload={'job_id': job.job_id, 'delivery_date': str(job.delivery_date)})
        try:
            send_notification(customer.email, f"Your job {job.job_id} has been created.", channel='email', payload={'job_id': job.job_id})
        except Exception:
            pass
    if getattr(settings, 'DEBUG', False):
        print(f"[MOCK NOTIFY] Job created {job.job_id} for {customer.phone} / {getattr(customer, 'email', '')}")

    pending.delete()
    return JsonResponse({'success': True, 'job_id': job.job_id})

# Following endpoints implement transitions from flowchart

@csrf_protect
def send_to_warehouse(request, job_id):
    """
    POST: optional courier_id, awb
    Sets status -> dispatched
    """
    job = get_object_or_404(RepairJob, job_id=job_id)
    courier_id = request.POST.get('courier_id')
    awb = request.POST.get('awb', '')
    if courier_id:
        try:
            courier = Courier.objects.get(id=courier_id)
            job.courier = courier
        except Courier.DoesNotExist:
            pass
    if awb:
        job.awb = awb
    job.status = 'dispatched'
    job.save()
    StatusHistory.objects.create(job=job, from_status='open', to_status='dispatched', note='Sent to warehouse')
    NotifyLog.objects.create(channel='mock', to=job.store.name, type='dispatched', payload={'job_id': job.job_id})
    return JsonResponse({'success': True, 'job_id': job.job_id, 'status': job.status})

@csrf_protect
def mark_received(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    job.status = 'received'
    job.save()
    StatusHistory.objects.create(job=job, from_status='dispatched', to_status='received', note='Received at warehouse')
    NotifyLog.objects.create(channel='mock', to=job.store.name, type='received', payload={'job_id': job.job_id})
    return JsonResponse({'success': True, 'job_id': job.job_id, 'status': job.status})

@csrf_protect
def mark_ready(request, job_id):
    # used when cobbler/warehouse marks item ready for pickup
    job = get_object_or_404(RepairJob, job_id=job_id)
    job.status = 'ready'
    job.save()

    # Record status transition
    StatusHistory.objects.create(job=job, from_status='received', to_status='ready', note='Ready for pickup')

    # Log notify and try to send notifications (best-effort)
    NotifyLog.objects.create(channel='mock', to=job.customer.phone, type='ready', payload={'job_id': job.job_id})
    try:
        send_notification(job.customer.phone, f"Your Job {job.job_id} is ready for pickup.", channel='sms', payload={'job_id': job.job_id})
    except Exception:
        pass

    # also notify by email if the customer has an email
    if getattr(job.customer, 'email', ''):
        NotifyLog.objects.create(channel='email', to=job.customer.email, type='ready', payload={'job_id': job.job_id})
        try:
            send_notification(job.customer.email, f"Your Job {job.job_id} is ready for pickup.", channel='email', payload={'job_id': job.job_id})
        except Exception:
            pass

    return JsonResponse({'success': True, 'job_id': job.job_id, 'status': job.status})

@csrf_protect
def generate_pickup_otp(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    otp = generate_otp_code()
    job.otp = otp
    job.otp_expiry = timezone.now() + datetime.timedelta(minutes=30)
    job.save()
    OtpLog.objects.create(phone=job.customer.phone, event='pickup_otp_generated', payload={'job_id': job.job_id, 'otp': otp})
    NotifyLog.objects.create(channel='mock', to=job.customer.phone, type='pickup_otp', payload={'otp': otp})
    if getattr(settings, 'DEBUG', False):
        print(f"[MOCK] Pickup OTP for {job.customer.phone}: {otp}")
    return JsonResponse({'success': True, 'job_id': job.job_id})

@csrf_protect
def upload_photo(request, job_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    job = get_object_or_404(RepairJob, job_id=job_id)
    
    if 'photo' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No photo uploaded'})
    
    photo = request.FILES['photo']
    JobPhoto.objects.create(job=job, file=photo)
    
    return JsonResponse({'success': True})

@csrf_protect
def verify_pickup(request, job_id):
    job = get_object_or_404(RepairJob, job_id=job_id)
    otp = request.POST.get('otp')
    if not otp:
        return JsonResponse({'success': False, 'error': 'OTP required'})
    if job.otp != otp:
        return JsonResponse({'success': False, 'error': 'Invalid OTP'})
    if job.otp_expiry and job.otp_expiry < timezone.now():
        return JsonResponse({'success': False, 'error': 'OTP expired'})
    job.status = 'closed'
    job.save()
    StatusHistory.objects.create(job=job, from_status='ready', to_status='closed', note='Customer pickup verified')
    OtpLog.objects.create(phone=job.customer.phone, event='pickup_verified', payload={'job_id': job.job_id})
    NotifyLog.objects.create(channel='mock', to=job.customer.phone, type='job_closed', payload={'job_id': job.job_id})
    return JsonResponse({'success': True, 'job_id': job.job_id})


@csrf_protect
def register(request):
    """Handle user registration from the login page register form.
    Creates a Django user (username uses email if provided, otherwise mobile),
    creates a Customer record, logs the user in, and redirects to LOGIN_REDIRECT_URL.
    """
    if request.method != 'POST':
        return redirect('login')

    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password')
    confirm = request.POST.get('confirm_password')
    mobile = request.POST.get('mobile', '').strip()

    # basic validation
    if not (name and email and password and confirm and mobile):
        # simple fallback: redirect back to login with a message could be improved
        return redirect('login')
    if password != confirm:
        return redirect('login')

    username = email or mobile

    # ensure unique username
    original_username = username
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{original_username}_{suffix}"
        suffix += 1

    created_user = User.objects.create_user(username=username, email=email, password=password, first_name=name)

    # create or update Customer
    try:
        customer, created = Customer.objects.get_or_create(phone=mobile, defaults={'name': name, 'email': email})
        if not created:
            customer.name = name
            customer.email = email
            customer.save()
    except Exception:
        # ignore customer creation errors for now
        pass

    # authenticate and login
    user = authenticate(username=username, password=password)
    if user is not None:
        auth_login(request, user)

    # mark user as registered so they are allowed to login
    try:
        from .models import LoginProfile
        lp, created = LoginProfile.objects.get_or_create(user=created_user)
        lp.is_registered = True
        lp.save()
    except Exception:
        # non-fatal if profile creation fails
        pass

    # redirect to configured login redirect (repairs home)
    redirect_to = getattr(settings, 'LOGIN_REDIRECT_URL', '/')
    return redirect(redirect_to)


@csrf_protect
def custom_login(request):
    """Custom login view that distinguishes between "user not registered" and "invalid password".

    WARNING: exposing whether a username exists is less secure; doing so because the user asked
    for explicit messages. Consider changing to a generic message in production.
    """
    # Use a single generic error message to avoid username enumeration
    generic_error = 'Invalid username or password.'
    error = None
    form = None

    # Determine 'next' (where to redirect after successful login)
    next_param = request.POST.get('next') or request.GET.get('next')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        # If the form validates credentials, check loginprofile and log user in.
        if form.is_valid():
            user_obj = form.get_user()
            try:
                lp = user_obj.loginprofile
                if not lp.is_registered:
                    # mark as invalid by adding a non-field error
                    form.add_error(None, generic_error)
                else:
                        auth_login(request, user_obj)
                        # Prefer the 'next' parameter if it's safe
                        try:
                            from django.utils.http import url_has_allowed_host_and_scheme
                            allowed = {request.get_host()}
                            if next_param and url_has_allowed_host_and_scheme(next_param, allowed_hosts=allowed):
                                return redirect(next_param)
                        except Exception:
                            pass
                        redirect_to = getattr(settings, 'LOGIN_REDIRECT_URL', '/')
                        return redirect(redirect_to)
            except Exception:
                # missing profile -> treat as not registered
                form.add_error(None, generic_error)
        else:
            # keep generic message; AuthenticationForm already adds non_field_errors
            error = generic_error
    else:
        form = AuthenticationForm()

    # GET or failed POST
    return render(request, 'repairs/login.html', {'error': error, 'form': form})

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import StaffProfile

@login_required
def dashboard(request):
    user = request.user

    # if admin user -> send to admin panel
    if user.is_superuser or user.is_staff:
        return redirect('/admin/')

    try:
        profile = user.staffprofile
    except StaffProfile.DoesNotExist:
        return HttpResponse("Role not assigned. Contact admin.")

    # Role-based redirect
    if profile.role == 'store':
        return redirect('repairs:store_dashboard')

    if profile.role == 'warehouse':
        return redirect('repairs:warehouse_dashboard')

    return HttpResponse("Invalid role. Contact admin.")


from django.contrib.auth.decorators import user_passes_test

def role_required(role):
    def check(user):
        try:
            return user.staffprofile.role == role
        except:
            return False
    return user_passes_test(check, login_url='/login/')


@login_required
@store_required
def store_dashboard(request):
    profile = request.user.staffprofile
    jobs = RepairJob.objects.filter(store=profile.store).order_by('-created_at')
    return render(request, 'repairs/store_dashboard.html', {'jobs': jobs})


@login_required
@warehouse_required
def warehouse_dashboard(request):
    jobs = RepairJob.objects.filter(status__in=['dispatched', 'received', 'repairing']).order_by('-updated_at')
    return render(request, 'repairs/warehouse_dashboard.html', {'jobs': jobs})
