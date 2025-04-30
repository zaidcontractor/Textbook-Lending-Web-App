"""
tasks.py

Defines background tasks for the textbook lending web application at the University of Virginia.
Includes a scheduled task to automatically generate due date reminder notifications 
(one week, one day, and one hour before an item's due time) for borrowers.
"""

from celery import shared_task
from django.utils import timezone
from .models import Item, Notification

@shared_task
def generate_due_notifications():
    now = timezone.now()
    windows = {
      'one_week': now + timezone.timedelta(weeks=1),
      'one_day':  now + timezone.timedelta(days=1),
      'one_hour': now + timezone.timedelta(hours=1),
    }

    for label, target in windows.items():
        items = Item.objects.filter(
          due_datetime__year=target.year,
          due_datetime__month=target.month,
          due_datetime__day=target.day,
          due_datetime__hour=target.hour,
        )
        for item in items:
            Notification.objects.get_or_create(
              user=item.borrower,
              item=item,
              kind=label,
            )