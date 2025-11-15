"""
Run from project root to test email sending via Django settings:

    python manage.py shell < test_send_email.py

Update the .env file with your SMTP credentials or set env vars before running.
"""
from django.core.mail import send_mail
from django.conf import settings

print('EMAIL_BACKEND:', settings.EMAIL_BACKEND)
print('EMAIL_HOST:', getattr(settings, 'EMAIL_HOST', None))
print('EMAIL_PORT:', getattr(settings, 'EMAIL_PORT', None))
print('DEFAULT_FROM_EMAIL:', settings.DEFAULT_FROM_EMAIL)

try:
    send_mail('Django test email', 'If you receive this, SMTP is working.', settings.DEFAULT_FROM_EMAIL, ['your_test_address@example.com'])
    print('send_mail called (check your inbox/spam).')
except Exception as e:
    print('Error sending email:', repr(e))
