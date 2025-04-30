"""
serializers.py

Defines serializers for the textbook lending web application at the University of Virginia.
Includes the NotificationSerializer to convert Notification model instances into JSON format 
for API responses, including related item details like title and due date.
"""

from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source='item.title', read_only=True)
    due_date   = serializers.DateField(source='item.due_date', read_only=True)
    class Meta:
        model  = Notification
        fields = [
            'id',
            'kind',
            'created',
            'read',
            'item_title',
            'due_date',
        ]