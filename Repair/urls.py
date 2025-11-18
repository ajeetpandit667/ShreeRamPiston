"""
URL configuration for Repair project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from repairs import views as repairs_views


# Consolidated URL patterns for the project
urlpatterns = [
    path('admin/', admin.site.urls),

    # auth: login/logout (login template path is registration/login.html)
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path("logout/", auth_views.LogoutView.as_view(next_page='/', template_name="registration/logout.html"), name="logout"),


    # password reset (Django builtin views)
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # your app urls (dashboard, role-based pages)
    # mount repairs app at site root
    path('', include('repairs.urls')),
    # also support the legacy /repairs/ prefix so both URLs work
    # redirect /repairs/ to site root where the app is mounted
    path('repairs/', RedirectView.as_view(url='/', permanent=False)),
]


# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    
    
# repair_project/urls.py



