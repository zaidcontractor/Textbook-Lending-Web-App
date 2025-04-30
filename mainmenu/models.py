"""
models.py

Defines all database models for the textbook lending web application at the University of Virginia.
These models represent the core objects and relationships needed to manage textbook items, 
user profiles, lending operations, collections, messaging, notifications, and user feedback.

Key Models:
- Item: Represents a textbook or other lendable item with status tracking, tagging, ownership, and due dates.
- Profile: Extends Django's User model with additional fields like role, major, and graduation year.
- Collection: Groups multiple items together with public/private visibility settings and access control.
- Tag and Class: Enable categorization of items and collections by subject matter.
- Message and Notification: Handle user-to-user communication and reminders about borrowed items.
- ItemReview and UserReview: Allow users to leave structured feedback on items and other users.
- CollectionAccessRequest: Supports requesting access to private collections.

Additional Features:
- Custom UUID generation for item identification.
- Automatic profile creation via Django signals upon user registration.
- Validation to enforce business rules, such as preventing private item conflicts.

These models serve as the foundation for the lending, borrowing, and review system across the platform.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from django.forms import ValidationError
from django.utils import timezone
from django.conf import settings

def short_uuid():
    return uuid.uuid4().hex[:10]

class Tag(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Class(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    slug = models.SlugField(unique=True)
    required_tags = models.ManyToManyField(Tag, related_name='required_by', blank=True)

    def __str__(self):
        return self.name

class Collection(models.Model):

    PUBLIC = 'public'
    PRIVATE = 'private'
    VISIBILITY_CHOICES = [
        (PUBLIC, 'Public'),
        (PRIVATE, 'Private'),
    ]
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    items = models.ManyToManyField('Item', related_name='collections_of', default=None)
    creator = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name="creator", default= None)
    visibility = models.CharField(
        choices=VISIBILITY_CHOICES,
        default=PUBLIC
    )
    access = models.ManyToManyField('Profile', related_name='access')
    identifier = models.CharField(max_length=10, unique=True, default=short_uuid, editable=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure only librarians can create private collections."""
        if self.creator.userRole == 0:  
            self.visibility = self.PUBLIC 
        super().save(*args, **kwargs)
        if self.visibility == self.PRIVATE:
            for item in self.items.all():
                if Collection.objects.filter(items=item, visibility=self.PRIVATE).exclude(id=self.id).exists():
                    raise ValidationError(f"Item '{item.uuid}' is already in another private collection.")

class CollectionAccessRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('denied', 'Denied')], default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} -> {self.collection.title} ({self.status})"

class ItemImage(models.Model):
    image = models.ImageField(upload_to='item_images/')
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.caption or f"Image {self.id}"

class Item(models.Model):
    STATUS_AVAILABLE = 'available'
    STATUS_IN_CIRCULATION = 'in_circulation'
    STATUS_REPAIRING = 'repairing'
    STATUS_LOST = 'lost'
    STATUS_REQUESTED = 'requested'
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_IN_CIRCULATION, 'In Circulation'),
        (STATUS_REPAIRING, 'Being Repaired'),
        (STATUS_LOST, 'Lost'),
        (STATUS_REQUESTED, 'Requested'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)
    location = models.CharField(max_length=255, blank=True, help_text="e.g. home library, work library")
    description = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, related_name='items', blank=True)
    images = models.ManyToManyField(ItemImage, related_name='items', blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='owned_items')
    due_date = models.DateField(
        blank=True,
        null=True,
        help_text="When this item is due back."
    )
    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='borrowed_items',
        blank=True,
        null=True,
        help_text="The user who currently has this item checked out."
    )

    @property
    def is_overdue(self):
        if not self.due_date:
            return False
        return timezone.localdate() > self.due_date

    def days_until_due(self):
        if not self.due_date:
            return None
        delta = self.due_date - timezone.localdate()
        return delta.days

    def __str__(self):
        status_display = dict(self.STATUS_CHOICES).get(self.status, self.status)
        tag_list = ", ".join(tag.name for tag in self.tags.all())
        return f"{self.title} [{status_display}] – Tags: {tag_list or 'None'}"

class TestObject(models.Model):
    important_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='media/profile_pics/', blank=True, null=True)
    userRole = models.IntegerField(default=0)  # 0 represents patron, 1 represents librarian
    major = models.CharField(max_length=255, blank=True, null=True)
    CLASS_CHOICES = [
        ('first_year', 'First Year'),
        ('second_year', 'Second Year'),
        ('third_year', 'Third Year'),
        ('fourth_year', 'Fourth Year'),
        ('grad_student', 'Grad Student'),
    ]
    class_year = models.CharField(max_length=20, choices=CLASS_CHOICES, blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user.username

class Notification(models.Model):
    KINDS = [
      ('one_week','One Week Out'),
      ('one_day','One Day Out'),
      ('one_hour','One Hour Out'),
    ]
    user      = models.ForeignKey(User, on_delete=models.CASCADE)
    item      = models.ForeignKey(Item, on_delete=models.CASCADE)
    kind      = models.CharField(max_length=20, choices=KINDS)
    created   = models.DateTimeField(auto_now_add=True)
    read      = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user','item','kind')

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender} to {self.recipient}: {self.content[:30]}"

class ItemReview(models.Model):
    rating = models.IntegerField(choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')])
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='item_reviews_given')

    class Meta:
        ordering = ['-created_at']
        unique_together = ('reviewer', 'item')

    def __str__(self):
        return f"{self.reviewer.username}'s review of {self.item.title}"

class UserReview(models.Model):
    rating = models.IntegerField(choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')])
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_received')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_reviews_given')

    class Meta:
        ordering = ['-created_at']
        unique_together = ('reviewer', 'reviewed_user')

    def __str__(self):
        return f"{self.reviewer.username}'s review of {self.reviewed_user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

