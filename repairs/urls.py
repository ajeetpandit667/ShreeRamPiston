# repairs/urls.py
from django.urls import path
from . import views

app_name = "repairs"

urlpatterns = [

    # -------------------------
    # HOME + BASIC PAGES
    # -------------------------
    path("", views.home, name="home"),
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/<str:job_id>/", views.job_detail, name="job_detail"),

    # -------------------------
    # OTP FLOW
    # -------------------------
    path("request-otp/", views.request_otp, name="request_otp"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),

    # -------------------------
    # STORE ACTIONS
    # -------------------------
    path("job/<str:job_id>/send-to-warehouse/", views.send_to_warehouse, name="send_to_warehouse"),

    # -------------------------
    # WAREHOUSE ACTIONS
    # -------------------------
    path("job/<str:job_id>/received/", views.mark_received, name="mark_received"),
    path("job/<str:job_id>/repairing/", views.mark_repairing, name="mark_repairing"),
    path("job/<str:job_id>/ready/", views.mark_ready, name="mark_ready"),
    path("job/<str:job_id>/not-repairable/", views.mark_not_repairable, name="mark_not_repairable"),
    path("job/<str:job_id>/dispatch-back/", views.dispatch_back_to_store, name="dispatch_back"),

    # -------------------------
    # OTP FOR PICKUP
    # -------------------------
    path("job/<str:job_id>/generate-pickup-otp/", views.generate_pickup_otp, name="generate_pickup_otp"),
    path("job/<str:job_id>/verify-pickup/", views.verify_pickup, name="verify_pickup"),

    # -------------------------
    # PHOTO UPLOAD
    # -------------------------
    path("job/<str:job_id>/upload-photo/", views.upload_photo, name="upload_photo"),

    # -------------------------
    # DASHBOARDS
    # -------------------------
    path("register/", views.register, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("store-dashboard/", views.store_dashboard, name="store_dashboard"),
    path("warehouse-dashboard/", views.warehouse_dashboard, name="warehouse_dashboard"),

    # -------------------------
    # ANALYTICS
    # -------------------------
    path("job-stats/", views.job_stats, name="job_stats"),
    
    # -------------------------
    # AI/ML
    # -------------------------
    path("api/delay-prediction/<str:job_id>/", views.api_delay_prediction, name="api_delay_prediction"),
    path("api/best-warehouse/", views.api_best_warehouse, name="best_warehouse"),

]
