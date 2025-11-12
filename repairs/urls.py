# repairs/urls.py
from django.urls import path
from . import views

app_name = 'repairs'

urlpatterns = [
    path('', views.home, name='home'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<str:job_id>/', views.job_detail, name='job_detail'),
    path('request-otp/', views.request_otp, name='request_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('jobs/<str:job_id>/send-to-warehouse/', views.send_to_warehouse, name='send_to_warehouse'),
    path('jobs/<str:job_id>/mark-received/', views.mark_received, name='mark_received'),
    path('jobs/<str:job_id>/mark-ready/', views.mark_ready, name='mark_ready'),
    path('jobs/<str:job_id>/generate-pickup-otp/', views.generate_pickup_otp, name='generate_pickup_otp'),
    path('jobs/<str:job_id>/verify-pickup/', views.verify_pickup, name='verify_pickup'),
    path('jobs/<str:job_id>/upload-photo/', views.upload_photo, name='upload_photo'),
]
