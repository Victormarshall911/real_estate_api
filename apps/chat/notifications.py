"""
Notification Service & Alerts for LandMarket.
Simulates instant Email, SMS, and Push notification dispatches to sellers/realtors
when new leads, chat inquiries, or escrow proposals arrive.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_notification_alert(recipient_user, event_type, subject, message, extra_data=None):
    """
    Dispatches a simulated background notification (Email / SMS) to a user.
    Can be run synchronously or wrapped in a Celery/background thread.
    """
    if not recipient_user:
        return False

    phone = getattr(recipient_user, 'phone_number', 'N/A')
    email = getattr(recipient_user, 'email', 'N/A')

    log_payload = {
        'timestamp': timezone.now().isoformat(),
        'recipient': f'{recipient_user.get_full_name()} (<{email}>, phone: {phone})',
        'event_type': event_type,
        'subject': subject,
        'message': message,
        'extra_data': extra_data or {},
    }

    logger.info(f'[NOTIFICATION SERVICE] Dispatching {event_type.upper()} Alert -> {email}: "{subject}"')
    # In a live production setup with Twilio/SendGrid configured, API calls would execute asynchronously here.
    return True
