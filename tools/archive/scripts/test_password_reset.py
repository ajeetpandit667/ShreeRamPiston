"""
Test password reset email flow.
Run from project root: python manage.py shell < test_password_reset.py
"""
from django.contrib.auth.models import User
from django.test import Client
from django.core.mail import send_mail

# Create a test user
User.objects.filter(username='testuser').delete()
user = User.objects.create_user('testuser', 'testuser@example.com', 'testpass123')

# Simulate password reset request
c = Client()
resp = c.post('/password-reset/', {'email': 'testuser@example.com'}, HTTP_HOST='127.0.0.1', follow=True)
print(f"Password reset request status: {resp.status_code}")
print(f"Redirected to: {resp.request.get('PATH_INFO')}")
print("\n[Password reset email should print to console above]")
