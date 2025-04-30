"""
tests.py

Defines automated tests for the textbook lending web application at the University of Virginia.
Covers unit tests and integration tests to verify user authentication, profile management, 
item borrowing and lending workflows, message handling, and item detail navigation.

Test Coverage Includes:
- Librarian and patron access to home pages, profiles, and borrowed/lent item pages.
- Borrowing requests from patrons and approval/denial by librarians.
- Correct state transitions for item status (e.g., available, requested, in circulation).
- Notification and messaging generation upon borrowing decisions.
- Navigation and display of item detail pages.

These tests ensure the reliability, correctness, and access control of critical lending operations 
within the platform.
"""

from datetime import timezone
from django.test import TestCase, Client
from .models import Profile, Item, Message
from django.urls import reverse
from django.contrib.auth import get_user_model
from .views import borrowed_items, home_page_router

class LibProfileViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username='user')
        self.user.set_password('passwerd')
        self.user.save()
        self.profile, _ = Profile.objects.get_or_create(user=self.user, defaults={'userRole': 1})
        self.url = reverse('librarian_home_page')

    def test_librarian_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_librarian_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, '/accounts/login/?next=/librarian_home_page/', status_code=302, target_status_code=200)

class PatronProfileViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username='user2')
        self.user.set_password('passwd')
        self.user.save()
        self.profile, _ = Profile.objects.get_or_create(user=self.user, defaults={'userRole': 0})
        self.url = reverse('home_page')

    def test_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

class LibrarianHomePageTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username='user3')
        self.user.set_password('paswd')
        self.user.save()
        self.profile, _ = Profile.objects.get_or_create(user=self.user, defaults={'userRole': 1})
        self.url = reverse('librarian_home_page')

    def test_logged_in_librarian_settings(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('librarian_settings'))
        self.assertEqual(response.status_code, 200)

    def test_logged_in_lent_items(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('lent_items'))
        self.assertEqual(response.status_code, 200)

    def test_logged_in_borrowed_items(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('borrowed_items'))
        self.assertEqual(response.status_code, 200)

    def test_logged_in_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_logged_in_required_materials(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('required_materials'))
        self.assertEqual(response.status_code, 200)

    def test_not_logged_in(self):
        response = self.client.get(reverse('librarian_settings'))
        self.assertRedirects(response, '/accounts/login/?next=/librarian_settings/', status_code=302, target_status_code=200)

class PatronHomePageTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(username='user4')
        self.user.set_password('pwd')
        self.user.save()
        self.profile, _ = Profile.objects.get_or_create(user=self.user, defaults={'userRole': 0})
        self.url = reverse('home_page')

    def test_logged_in_lent_items(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('lent_items'))
        self.assertEqual(response.status_code, 200)

    def test_logged_in_borrowed_items(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('borrowed_items'))
        self.assertEqual(response.status_code, 200)

    def test_logged_in_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_logged_in_required_materials(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('required_materials'))
        self.assertEqual(response.status_code, 200)

    def test_not_logged_in(self):
        response = self.client.get(reverse('lent_items'))
        self.assertRedirects(response, '/accounts/login/?next=/lent_items/', status_code=302, target_status_code=200)

    class BorrowedItemsPageTestPatron(TestCase):
        def setUp(self):
            self.client = Client()
            User = get_user_model()
            self.user, _ = User.objects.get_or_create(username='user4')
            self.user.set_password('pwd')
            self.user.save()
            self.profile, _ = Profile.objects.get_or_create(user=self.user, defaults={'userRole': 0})
            self.owner, _ = User.objects.get_or_create(username='user_alpha')
            self.borrower, _ = User.objects.get_or_create(username='user_gamma')
            self.item, _ = Item.objects.get_or_create(title='To be borrowed', status=Item.STATUS_AVAILABLE,
                                                      location='Clark Hall',
                                                      description='The item is for testing purposes only',
                                                      owner=self.owner)
            self.base_url = reverse("home_page")
            self.client.force_login(self.user)
            self.gotten_into_url = reverse("borrowed_items")
            self.go_through = reverse("available_to_requested", args=[self.item.uuid])

        def test_redirect_back_to_home_page(self):
            response = self.client.get(reverse("home_page"))
            self.assertEqual(response.status_code, 200)

        def test_form_if_request_is_sent(self):
            first_response = self.client.get(self.gotten_into_url)
            self.assertContains(first_response, "To be borrowed")
            borrowing = self.client.post(self.go_through)
            self.assertRedirects(borrowing, '/accounts/login/?next=/home_page/', status_code=302,
                                 target_status_code=200)
            self.item.refresh_from_db()
            self.assertEqual(self.item.status, Item.STATUS_REQUESTED)
            self.assertEqual(self.item.location, 'Clark Hall')
            self.assertEqual(self.item.borrower, self.borrower)
            aftermath = self.client.post(self.gotten_into_url)
            self.assertNotContains(aftermath, "To be borrowed")

    class BorrowedItemsPageTestLibrarian(TestCase):
        def setUp(self):
            self.client = Client()
            User = get_user_model()
            self.user, _ = User.objects.get_or_create(username='user4')
            self.user.set_password('pwd')
            self.user.save()
            self.profile, _ = Profile.objects.get_or_create(user=self.user, defaults={'userRole': 1})
            self.owner, _ = User.objects.get_or_create(username='user_theta')
            self.borrower, _ = User.objects.get_or_create(username='user_chi')
            self.item, _ = Item.objects.get_or_create(title='To be reviewed', status=Item.STATUS_REQUESTED,
                                                      location='Clark Hall',
                                                      description='The item is for testing purposes only',
                                                      owner=self.owner,
                                                      borrower=self.borrower)
            self.base_url = reverse("librarian_home_page")
            self.client.force_login(self.user)
            self.gotten_into_url = reverse("borrowed_items")
            self.go_through = reverse("requested_to_in_circulation", args=[self.item.uuid])
            self.message, _ = Message.objects.get_or_create(sender=self.borrower, recipient=self.owner)

        def test_redirect_back_to_home_page(self):
            response = self.client.get(reverse("home_page_router"))
            self.assertEqual(response.status_code, 200)

        def test_form_if_request_is_sent_yes(self):
            first_response = self.client.get(self.gotten_into_url)
            self.assertContains(first_response, "To be borrowed")
            due_date = timezone.localdate() + timezone.timedelta(days=7)
            response = self.client.post(self.base_url, {
                'item': self.item.uuid,
                'yes': 'Confirm',
                'due_date': due_date
            })
            self.assertRedirects(borrowing, reverse('librarian_home_page'), status_code=302, target_status_code=200)
            self.item.refresh_from_db()
            self.assertEqual(self.item.status, Item.STATUS_IN_CIRCULATION)
            self.assertEqual(self.item.location, 'Clark Hall')
            self.assertEqual(self.item.borrower, self.borrower)
            self.assertEqual(self.item.due_date, due_date)
            aftermath = self.client.post(self.gotten_into_url)
            self.assertNotContains(aftermath, "To be borrowed")

            messages = Message.objects.filter(item=self.item, recipient=self.borrower)
            self.assertTrue(messages.exists())
            self.assertRedirects(response, reverse('home_page_router'))

        def test_form_if_request_is_sent_no(self):
            first_response = self.client.get(self.gotten_into_url)
            self.assertContains(first_response, "To be borrowed")
            due_date = timezone.localdate() + timezone.timedelta(days=7)
            response = self.client.post(self.base_url, {
                'item': self.item.uuid,
                'no': 'Deny',
            })
            self.assertRedirects(borrowing, reverse("librarian_home_page"), status_code=302, target_status_code=200)
            self.item.refresh_from_db()
            self.assertEqual(self.item.status, Item.STATUS_AVAILABLE)
            self.assertEqual(self.item.location, 'Clark Hall')
            self.assertIsNone(self.item.borrower)
            self.assertEqual(self.item.due_date, due_date)
            aftermath = self.client.post(self.gotten_into_url)
            self.assertNotContains(aftermath, "To be borrowed")

            messages = Message.objects.filter(item=self.item, recipient=self.borrower)
            self.assertTrue(messages.exists())
            self.assertIn("denied", messages.last().content.lower())

            self.assertRedirects(response, reverse('home_page_router'))

    class ItemDetailNavigationTests(TestCase):
        def setUp(self):
            self.client = Client()
            User = get_user_model()

            self.user = User.objects.create_user(username='patronico', password='testpassiere',
                                                 email='patron@example.com')
            self.profile, _ = Profile.objects.get_or_create(user=self.user, userRole=0)

            self.client.login(username='patronico', password='testpassiere')

            self.item1, _ = Item.objects.get_or_create(
                title='Physics Textbook',
                status='available',
                location='Shelf A',
                description='Covers basic physics concepts.',
                owner=self.user
            )
            self.item2, _ = Item.objects.get_or_create(
                title='Chemistry Textbook',
                status='available',
                location='Shelf B',
                description='Organic chemistry fundamentals.',
                owner=self.user
            )

        def test_item_detail_page_displays_correct_item(self):
            # Go to item detail page of item1
            response = self.client.get(reverse('item_detail', args=[self.item1.uuid]))

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Physics Textbook')
            self.assertNotContains(response, 'Chemistry Textbook')

            # Go to item detail page of item2
            response = self.client.get(reverse('item_detail', args=[self.item2.uuid]))

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Chemistry Textbook')
            self.assertNotContains(response, 'Physics Textbook')