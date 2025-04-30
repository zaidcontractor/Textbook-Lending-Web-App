"""
admin.py

This file configures the Django admin interface for the textbook lending web application 
at the University of Virginia. It registers various models—such as TestObject, Profile, 
Class, Tag, Item, Message, Notification, and Collection—so that administrators can view, 
add, edit, and delete records directly through the Django admin site.

Customizations:
- A customized admin view for the Profile model is provided, displaying associated user details 
  like username, email, first name, last name, and password.
- The Tag model is also registered with a basic admin configuration.

The admin interface supports management of textbook listings, user profiles, 
communication, and organizational features essential for the app's operation.
"""

from django.contrib import admin
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .models import TestObject,Profile, Class, Tag, Item, Message, Notification, Collection

from mainmenu.models import Tag

admin.site.register(TestObject)
admin.site.register(Class)
admin.site.register(Collection)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_username', 'user_email', 'userRole', 'user_first_name', 'user_last_name', 'user_password')

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Username'  

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def user_first_name(self, obj):
        return obj.user.first_name
    user_first_name.short_description = 'First Name'

    def user_last_name(self, obj):
        return obj.user.last_name
    user_last_name.short_description = 'Last Name'

    def user_password(self, obj):
        return obj.user.password
    user_password.short_description = 'Password'

admin.site.register(Profile, ProfileAdmin)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'uuid', 'status', 'owner') 

admin.site.register(Item, ItemAdmin)