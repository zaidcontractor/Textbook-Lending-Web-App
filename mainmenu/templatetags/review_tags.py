from django import template
from django.db.models import Avg

register = template.Library()

@register.filter
def avg_rating(reviews):
    """Calculate the average rating from a queryset of reviews."""
    if reviews.exists():
        return round(reviews.aggregate(Avg('rating'))['rating__avg'], 1)
    return 0 