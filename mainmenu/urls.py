"""
urls.py

Defines URL routing for the textbook lending web application at the University of Virginia.
Maps URL patterns to view functions, enabling navigation across key parts of the platform 
such as authentication, item management, collections, messaging, profiles, and reviews.

Main Routes:
- User authentication: login, logout, role switching (patron ↔ librarian)
- Item operations: add, edit, view, delete, request, borrow, and review textbooks
- Profile management: view, edit, upload profile pictures
- Collection operations: create, edit, view, delete, and request access
- Messaging and notifications between users
- Home page routing based on user role (librarian vs patron)

This configuration controls how users interact with the major functionalities of the platform.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_page, name="index"),
    path("logout/", views.logout_view, name="logout"),
    path("homepage/", views.home_page_router, name='home_page'),
    path("login_page/", views.login_page, name="login_page"),
    path("unauth/", views.unauth_home_page, name="unauth_home_page"),
    path('classes/create/', views.class_create, name='class_create'),
    path('classes/<slug:slug>/', views.class_detail, name='class_detail'),
    path('classes/<slug:slug>/add_required_tag/', views.add_required_tag, name='add_required_tag'),
    path('classes/<slug:slug>/unlink_required_tag/<int:tag_id>/', views.unlink_required_tag, name='unlink_required_tag'),
    path("profile/", views.profile, name='profile'),
    path("profile/<int:user_id>/", views.profile, name='user_profile'),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path('classes/<slug:slug>/material_create/', views.material_create, name='material_create'),
    path("messaging/", views.messaging, name='messaging'),
    path("lent_items/", views.lent_items, name='lent_items'),
    path("borrowed_items/", views.borrowed_items, name='borrowed_items'),
    path("mark_item_returned/<uuid:uuid>/", views.mark_item_returned, name='mark_item_returned'),
    path("librarian_home_page/", views.librarian_home_page, name='librarian_home_page'),
    path("homepage/", views.home_page_router, name='home_page_router'),
    path("required_materials/", views.required_materials, name='required_materials'),
    path("upload_pfp/", views.upload_pfp, name="upload_pfp"),
    path("librarian_settings/", views.librarian_settings, name='librarian_settings'),
    path("patron_to_librarian/", views.patron_to_librarian, name='patron_to_librarian'),
    path("librarian_requests/", views.librarian_requests, name='librarian_requests'),
    path('add-item/', views.add_item, name='add_item'),
    path('add-item-submit/', views.add_item_submit, name='add_item_submit'),
    path('tag_create/', views.tag_create, name='tag_create'),
    path('available_to_requested/', views.available_to_requested, name='available_to_requested'),
    path('requested_to_in_circulation/', views.requested_to_in_circulation, name='requested_to_in_circulation'),
    path('item_post/', views.item_post, name='item_post'),
    path('items/<uuid:uuid>/', views.item_detail, name='item_detail'),
    path('items/<uuid:uuid>/delete/', views.delete_item, name='delete_item'),
    path('items/<uuid:uuid>/edit/', views.edit_item, name='edit_item'),
    path('items/<uuid:item_uuid>/review/', views.submit_item_review, name='submit_item_review'),
    path('reviews/item/<int:review_id>/delete/', views.delete_item_review, name='delete_item_review'),
    path('users/<int:user_id>/review/', views.submit_user_review, name='submit_user_review'),
    path('reviews/user/<int:review_id>/delete/', views.delete_user_review, name='delete_user_review'),
    path('collections', views.collection, name = 'collections'),
    path('collection/<int:collection_id>/', views.collection_detail, name='collection_detail'),
    path('collection/<int:collection_id>/edit/', views.edit_collection, name='edit_collection'),
    path('collection/<int:collection_id>/delete/', views.delete_collection, name='delete_collection'),
    path('reviews/', views.user_reviews, name='user_reviews'),
    path('collection/<int:collection_id>/request-access/', views.request_access, name='request_access'),
    path('process_collection_access_request/', views.process_collection_access_request, name='process_collection_access_request'),
]