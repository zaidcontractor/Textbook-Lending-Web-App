"""
celery.py

Initializes Celery for the textbook lending web app at the University of Virginia.
Configures Celery to load settings from Django and auto-discover tasks across apps.
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'supplysite.settings')

app = Celery('mainmenu')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()