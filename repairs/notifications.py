# repairs/notifications.py
from twilio.rest import Client
from django.conf import settings
from django.core.mail import send_mail
from .models import NotifyLog
import logging
logger = logging.getLogger(__name__)


def send_notification(to, text, channel='mock', payload=None):
    """
    Send notifications via SMS (Twilio), email (Django email backend), or mock for development.
    Args:
        to: Recipient (phone number for SMS or email address for email)
        text: Message content
        channel: 'sms' for Twilio SMS, 'email' for email, anything else for mock
        payload: Optional additional data
    """
    # Log notification attempt
    NotifyLog.objects.create(
        channel=channel,
        to=to,
        type='generic',
        payload=payload or {'text': text}
    )

    if channel == 'sms':
        try:
            client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH)
            client.messages.create(body=text, from_=settings.TWILIO_FROM, to=to)
            return True
        except Exception as e:
            if getattr(settings, 'DEBUG', False):
                # During development print simple message
                print(f"SMS sending failed: {str(e)}")
            logger.exception('SMS sending failed')
            return False

    if channel == 'email':
        try:
            subject = payload.get('subject') if payload and payload.get('subject') else 'Notification from Shree Ram Piston'
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'TWILIO_FROM', None) or 'no-reply@example.com'
            # send_mail returns number of successfully delivered messages
            send_mail(subject, text, from_email, [to], fail_silently=False)
            return True
        except Exception as e:
            if getattr(settings, 'DEBUG', False):
                print(f"Email sending failed: {str(e)}")
            logger.exception('Email sending failed')
            return False

    # Fallback: mock
    if getattr(settings, 'DEBUG', False):
        print(f"[MOCK] {to}: {text}")
    logger.debug('Mock notification to %s: %s', to, text)
    return True
