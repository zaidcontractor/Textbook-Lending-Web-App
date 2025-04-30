from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from mainmenu.models import Item, Message

class Command(BaseCommand):
    help = 'Checks for items due in one day and creates warning messages'

    def handle(self, *args, **options):
        # Get items due in exactly one day
        tomorrow = timezone.now() + timedelta(days=1)
        items_due_tomorrow = Item.objects.filter(
            status='in_circulation',
            due_date__year=tomorrow.year,
            due_date__month=tomorrow.month,
            due_date__day=tomorrow.day
        )

        for item in items_due_tomorrow:
            # Check if a warning message was already sent today
            today = timezone.now().date()
            existing_message = Message.objects.filter(
                item=item,
                sender=item.owner,
                recipient=item.borrower,
                timestamp__year=today.year,
                timestamp__month=today.month,
                timestamp__day=today.day,
                content__contains='due tomorrow'
            ).exists()

            if not existing_message:
                Message.objects.create(
                    sender=item.owner,
                    recipient=item.borrower,
                    item=item,
                    content=f"Reminder: The item '{item.title}' is due tomorrow ({item.due_date.strftime('%B %d, %Y')}). Please return it on time."
                )
                self.stdout.write(self.style.SUCCESS(f'Created warning message for item {item.title}'))

        self.stdout.write(self.style.SUCCESS('Finished checking due dates')) 