"""
views.py

Defines the main view functions for the textbook lending web application at the University of Virginia.
Handles user interactions, page rendering, form submissions, access control, and API endpoints.

Key Functionalities:
- User authentication and session management (login, logout, home page routing).
- Item lifecycle operations: listing, borrowing, lending, editing, and deleting textbooks.
- Profile management: view, edit, upload profile pictures, and display user reviews.
- Messaging system: sending and receiving messages tied to item transactions and collection access.
- Collection management: create, edit, view, delete collections and handle access requests.
- Class and tag management: create, view, and organize required textbook materials.
- Review system: submit and manage item and user reviews.
- Notification API: retrieve unread notifications for authenticated users.

These views power all major features of the platform, enabling seamless textbook lending and borrowing 
across patrons and librarians.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.messages.storage import default_storage
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.template.defaultfilters import slugify
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Avg
from .forms import ProfileForm, ItemReviewForm, UserReviewForm, DueDateForm

from .forms import ItemForm, CollectionForm
from .models import *
from django.contrib.auth import logout
from django.template import loader
from django.urls import reverse
from django.core.files.storage import default_storage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Notification, Collection, CollectionAccessRequest
from .serializers import NotificationSerializer
from django.contrib import messages

def login_page(request):
    if request.user.is_authenticated:
        return redirect('home_page_router')   
    return render(request, "login.html")

def index(request):
    try:
        info = TestObject.objects.get(pk=1)
    except TestObject.DoesNotExist:
        return render(request, "mainmenu/index.html", {"info": "This text only appears locally"})
    return render(request, "mainmenu/index.html", {"info": info.important_text})    

def logout_view(request):
    logout(request)
    return redirect("login_page")

def home_page_router(request):
    print("In home_page_router")
    if request.user.is_authenticated:
        print(f"User is authenticated, role: {request.user.profile.userRole}")
        if request.user.profile.userRole == 0:
            print("Rendering home_page.html")
            return home_page(request)
        elif request.user.profile.userRole == 1:
            print("Rendering librarian_home_page.html")
            return librarian_home_page(request)
    print("User not authenticated, rendering unauth_home.html")
    return unauth_home_page(request)

def unauth_home_page(request):
    """
    For anonymous users, return items that are either:
      - Not in any collection, OR
      - In collections that are all public.
    This is achieved by excluding any item that appears in any collection with visibility set to 'private'.
    """
    q = request.GET.get('q', '')
    # Exclude items that are in any private collections.
    base_items = Item.objects.exclude(collections_of__visibility='private').distinct()
    
    if q:
        items = base_items.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(location__icontains=q) |
            Q(tags__name__icontains=q)
        ).distinct().order_by('-id')
    else:
        items = base_items.order_by('-id')
    
    context = {
        'items': items,
        'q': q,
    }
    return render(request, 'unauth_home.html', context)

@login_required
def home_page(request):
    print("In home_page, rendering home_page.html")
    q = request.GET.get('q', '')

    private_item_ids = Item.objects.filter(collections_of__visibility='private').values_list('id', flat=True).distinct()
    items = Item.objects.exclude(id__in=private_item_ids).distinct()

    if q:
        items = items.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(location__icontains=q) |
            Q(tags__name__icontains=q)
        ).distinct().order_by('-id')
    else:
        items = items.order_by('-id')

    context = {
        'tags': Tag.objects.all(),
        'items': items,
        'q': q,
    }
    return render(request, 'home_page.html', context)

@login_required
def librarian_home_page(request):
    print("In librarian_home_page, rendering librarian_home_page.html")
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            for f in request.FILES.getlist('images'):
                img = ItemImage.objects.create(image=f)
                item.images.add(img)
            return redirect('librarian_home_page')
    else:
        form = ItemForm()

    q = request.GET.get('q', '')
    if q:
        items = Item.objects.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(location__icontains=q) |
            Q(tags__name__icontains=q)
        ).distinct().order_by('-id')
    else:
        items = Item.objects.all().order_by('-id')

    return render(request, "librarian_home_page.html", {
        'form': form,
        'items': items,
        'q': q,
    })


def profile(request, user_id=None):
    if user_id:
        user = get_object_or_404(User, id=user_id)
    else:
        user = request.user
    collections = Collection.objects.all().filter(creator=user.profile)

    if not request.user.is_authenticated:
        collections = collections.exclude(visibility='private')

    user_reviews = UserReview.objects.filter(reviewed_user=user)
    avg_user_rating = user_reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    if avg_user_rating:
        avg_user_rating = round(avg_user_rating, 1)
    
    # Get the current user's review if they're viewing someone else's profile
    user_review = None
    if request.user.is_authenticated and user != request.user:
        user_review = UserReview.objects.filter(reviewer=request.user, reviewed_user=user).first()
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')

    else:
        form = ProfileForm(instance=user.profile)
    
    context = {
        'form': form,
        'profile_user': user,
        'is_own_profile': user == request.user,
        'user_reviews': user_reviews,
        'avg_user_rating': avg_user_rating,
        'user_review': user_review,
        'collections': collections,
    }
    return render(request, 'mainmenu/profile.html', context)

@login_required
def upload_pfp(request):
    if request.method == 'POST' and request.FILES.get('pfp'):
        profile = request.user.profile
        profile.profile_picture = request.FILES['pfp']
        profile.save()
    return redirect('/profile/')

@login_required
def messaging(request):
    received = Message.objects.filter(recipient=request.user).order_by('-timestamp')
    sent = Message.objects.filter(sender=request.user).order_by('-timestamp')
    return render(request, 'messaging.html', {'received': received, 'sent': sent})

@login_required
def lent_items(request):
    lent_items_list = Item.objects.filter(owner=request.user, status='in_circulation')
    listed_items_list = Item.objects.filter(owner=request.user, status='available')
    context = {
        'lent_items_list': lent_items_list,
        'listed_items_list': listed_items_list,
    }
    return render(request, "lent_items.html", context)

@login_required
def mark_item_returned(request, uuid):
    item = get_object_or_404(Item, uuid=uuid)
    
    # Check if user is the owner of the item
    if item.owner != request.user:
        return HttpResponseForbidden("You do not have permission to mark this item as returned.")
    
    # Check if item is actually in circulation
    if item.status != Item.STATUS_IN_CIRCULATION:
        return HttpResponseForbidden("This item is not currently in circulation.")
    
    if request.method == 'POST':
        item.status = Item.STATUS_AVAILABLE
        item.borrower = None
        item.due_date = None
        item.save()
        
        # Create a message to notify the borrower
        if item.borrower:
            Message.objects.create(
                sender=request.user,
                recipient=item.borrower,
                item=item,
                content=f"The item '{item.title}' has been marked as returned by the librarian."
            )
        
        return redirect('lent_items')
    
    return HttpResponseForbidden("Invalid request method.")

@login_required
def borrowed_items(request):
    if request.user.profile.userRole == 1:
        return HttpResponseRedirect(reverse('librarian_requests'))
    else:  
        borrowed_item_list = Item.objects.filter(borrower=request.user, status='in_circulation')
        available_items = Item.objects.filter(status='available')
        context = {
            'borrowed_item_list': borrowed_item_list,
            'available_items': available_items,
        }
        return render(request, "borrowed_items.html", context)

def available_to_requested(request):
    available_items = Item.objects.filter(status='available')
    try:
        selected_item = available_items.get(pk=request.POST['item'])
    except (KeyError, Item.DoesNotExist):
        return render(request, "borrowed_items.html", {"available_items": available_items})
    else:
        selected_item.status = 'requested'
        selected_item.save()

        Message.objects.create(
            sender=request.user,
            recipient=selected_item.owner,
            item=selected_item,
            content=f"{request.user.username} has requested to borrow your textbook: {selected_item.title}"
        )

        return HttpResponseRedirect(reverse('home_page_router'))

#https://stackoverflow.com/questions/866272/how-can-i-build-multiple-submit-buttons-django-form
@login_required
def requested_to_in_circulation(request):
    requested_items = Item.objects.filter(status='requested')
    try:
        selected_item = requested_items.get(pk=request.POST['item'])
    except (KeyError, Item.DoesNotExist):
        return render(request, "borrowed_items.html", {"requested_items": requested_items})
    else:
        if 'yes' in request.POST:
            form = DueDateForm(request.POST)
            if form.is_valid():
                selected_item.status = 'in_circulation'
                selected_item.borrower = selected_item.message_set.filter(item=selected_item).last().sender
                selected_item.due_date = form.cleaned_data['due_date']
                selected_item.save()

                patron = selected_item.borrower
                patron.borrowed_items.add(selected_item)

                Message.objects.create(
                    sender=request.user, 
                    recipient=patron,
                    item=selected_item,
                    content=f"Your request to borrow '{selected_item.title}' has been accepted. The item is due back on {selected_item.due_date.strftime('%B %d, %Y')}."
                )
                return HttpResponseRedirect(reverse('home_page_router'))
            else:
                return render(request, "set_due_date.html", {
                    "form": form,
                    "item": selected_item
                })

        elif 'no' in request.POST:
            selected_item.status = 'available'
            selected_item.save()

            patron_message = selected_item.message_set.filter(item=selected_item).last()
            if patron_message:
                Message.objects.create(
                    sender=request.user,  
                    recipient=patron_message.sender,
                    item=selected_item,
                    content=f"Your request to borrow '{selected_item.title}' has been denied. The item is now available again."
                )

            return HttpResponseRedirect(reverse('home_page_router'))

@login_required
def librarian_settings(request):
    patron_list = Profile.objects.filter(userRole=0)
    context = {
        "patron_list": patron_list,
    }
    return render(request, "librarian_settings.html", context )

def class_detail(request, slug):
    class_obj = get_object_or_404(Class, slug=slug)
    required_tags = class_obj.required_tags.all()
    available_tags = Tag.objects.exclude(id__in=required_tags.values_list('id', flat=True))
    context = {
        'class_obj': class_obj,
        'required_tags': required_tags,
        'available_tags': available_tags,
    }
    return render(request, 'class_detail.html', context)

def patron_to_librarian(request):
    patron_list = Profile.objects.filter(userRole=0)
    if request.method == 'POST':
        selected_ids = request.POST.getlist("patrons")
        if not selected_ids:
            return render(request, "librarian_settings.html", {"patron_list": patron_list})
        
        for patron_id in selected_ids:
            try:
                patron = Profile.objects.get(pk=patron_id)
                patron.userRole = 1
                patron.save()
            except Profile.DoesNotExist:
                continue

        return HttpResponseRedirect(reverse("home_page_router"))
    return render(request, "librarian_settings.html", {"patron_list": patron_list})

def required_materials(request):
    q = request.GET.get('q', '')
    if q:
        classes = Class.objects.filter(name__icontains=q) | Class.objects.filter(description__icontains=q)
    else:
        classes = Class.objects.all()
    return render(request, 'required_materials.html', {'classes': classes, 'q': q})

@login_required
def add_item(request):
    if request.user.profile.userRole != 1:
        return redirect('home_page')
    classes = Class.objects.all()
    tags = Tag.objects.all()
    return render(request, "add_item.html", {
        "classes": classes,
        "tags": tags
    })

@login_required
def class_create(request):
    if request.user.profile.userRole != 1:
        return HttpResponseForbidden("You are not authorized to add a class.")
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        if not name or not description:
            return redirect('home_page')
        base_slug = slugify(name)
        if not base_slug:  
            base_slug = "class"  
        slug = base_slug
        counter = 1
        while Class.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        new_class = Class.objects.create(name=name, description=description, slug=slug)
        return redirect('class_detail', slug=new_class.slug)
    return redirect('home_page')

@login_required
def tag_create(request):
    if request.user.profile.userRole != 1:
        return HttpResponseForbidden("You are not authorized to add a tag.")
    if request.method == "POST":
        tag_name = request.POST.get("tag_name", "").strip()
        if tag_name:
            Tag.objects.create(name=tag_name)
        return redirect('librarian_home_page')
    return redirect('librarian_home_page')

@login_required
def add_item_submit(request):
    if request.user.profile.userRole != 1:
        return redirect('home_page')
    if request.method == 'POST':
        title = request.POST.get('title')
        status = request.POST.get('status')
        location = request.POST.get('location', '')
        description = request.POST.get('description', '')

        new_item = Item(
            title=title,
            status=status,
            location=location,
            description=description,
            owner=request.user
        )
        new_item.save()
        tag_ids = request.POST.getlist('tags')
        for tag_id in tag_ids:
            tag = Tag.objects.get(id=tag_id)
            new_item.tags.add(tag)
        images = request.FILES.getlist('images')
        for img in images:
            item_image = ItemImage(image=img)
            item_image.save()
            new_item.images.add(item_image)
        return redirect('librarian_home_page')
    return redirect('add_item')

    '''
    if request.FILES.get('item_pic'):
        item_pic = request.FILES['item_pic']
        clean_name = ''.join(c for c in identifier if c.isalnum() or c in '._- ')
        clean_name = clean_name.replace(' ', '_').lower()
        file_url = default_storage.save(f"media/item_pics/{clean_name}.png", item_pic)   
    '''

@login_required
def material_create(request, slug):
    if request.user.profile.userRole != 1:
        return HttpResponseForbidden("You are not authorized to add material.")
    class_obj = get_object_or_404(Class, slug=slug)
    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        is_available = request.POST.get("is_available") == "on"
        tag_ids = request.POST.getlist("tags")
        new_item = Item.objects.create(identifier=identifier, is_available=is_available)
        if tag_ids:
            valid_tags = Tag.objects.filter(id__in=tag_ids)
            new_item.tags.add(*valid_tags)
        class_obj.items.add(new_item)
        return redirect('class_detail', slug=slug)
    return redirect('class_detail', slug=slug)

@login_required
def unlink_required_tag(request, slug, tag_id):
    if request.user.profile.userRole != 1:
        return HttpResponseForbidden("You are not authorized to remove a required tag.")
    class_obj = get_object_or_404(Class, slug=slug)
    tag = get_object_or_404(Tag, id=tag_id)
    class_obj.required_tags.remove(tag)
    return redirect('class_detail', slug=slug)

@login_required
def add_required_tag(request, slug):
    if request.user.profile.userRole != 1:
        return HttpResponseForbidden("You are not authorized to add a required tag.")
    class_obj = get_object_or_404(Class, slug=slug)
    if request.method == "POST":
        tag_id = request.POST.get("tag_id")
        if tag_id:
            tag = get_object_or_404(Tag, id=tag_id)
            class_obj.required_tags.add(tag)
        return redirect('class_detail', slug=slug)
    return redirect('class_detail', slug=slug)

@login_required
def item_post(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            for f in request.FILES.getlist('images'):
                img = ItemImage.objects.create(image=f)
                item.images.add(img)
            item.owner = request.user
            item.save()
            return redirect('librarian_home_page')
    else:
        form = ItemForm()
    return render(request, 'librarian_home_page.html', {
        'form': form
    })

def item_detail(request, uuid):
    item = get_object_or_404(Item, uuid=uuid)
    user_review = None
    if request.user.is_authenticated:
        user_review = ItemReview.objects.filter(reviewer=request.user, item=item).first()
    return render(request, 'item_detail.html', {
        'item': item,
        'user_review': user_review
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_notifications(request):
    qs = Notification.objects.filter(user=request.user, read=False)
    serializer = NotificationSerializer(qs, many=True)
    return Response(serializer.data)

def collection(request):
    q = request.GET.get("q", "")
    user_collections = []

    if request.method == "POST":
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = form.save(commit=False)
            if not collection.creator_id:
                collection.creator = request.user.profile
            collection.save()
            form.save_m2m()
            return redirect('collections')
    else:
        form = CollectionForm()
    # Only filter for user-owned collections if logged in
    if request.user.is_authenticated:
        user_collections = Collection.objects.filter(creator=request.user.profile).filter()

    collections = Collection.objects.all()

    if q:
        if request.user.is_authenticated:
            user_collections = Collection.objects.filter(creator=request.user.profile).filter(Q(name__icontains=q))
        collections = collections.filter(Q(name__icontains=q))


    if not request.user.is_authenticated:
        collections = collections.filter(visibility='public')



    private_item_ids = Item.objects.filter(collections_of__visibility='private').values_list('id', flat=True).distinct()
    items = Item.objects.exclude(id__in=private_item_ids).distinct()

    return render(request, "collection.html", {
        "collections": collections,
        "user_collections": user_collections,
        "items": items,
        "form": form,
        "q": q,
    })

def collection_detail(request, collection_id):
    q = request.GET.get('q', '')
    collection = get_object_or_404(Collection, id=collection_id)
    items = collection.items.all()  
    if q:
        items = items.filter(Q(title__icontains=q))
    return render(request, 'collection_detail.html', {
        'collection': collection,
        'items': items,
    })

def edit_collection(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)

    private_item_ids = Item.objects.filter(
        collections_of__visibility='private'
    ).values_list('id', flat=True)

    allowed_items = Item.objects.filter(
        Q(id__in=collection.items.values_list('id', flat=True)) |
        ~Q(id__in=private_item_ids)
    ).distinct()

    if request.method == 'POST':
        form = CollectionForm(request.POST, instance=collection)
    else:
        form = CollectionForm(instance=collection)

    if request.user.profile.userRole == 0:  # Patron
        form.fields['visibility'].choices = [('public', 'Public')]


    form.fields['items'].queryset = allowed_items

    if request.method == 'POST' and form.is_valid():
        updated_collection = form.save(commit=False)
        updated_collection.save()
        form.save_m2m()
        return redirect('collection_detail', collection_id)

    return render(request, 'edit_collection.html', {
        'form': form,
        'collection': collection,
    })


@login_required
def request_access(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)

    CollectionAccessRequest.objects.get_or_create(user=request.user, collection=collection)
    Message.objects.create(
        sender=request.user,
        recipient=collection.creator.user, 
        content=f"{request.user.username} has requested access to your collection: '{collection.name}'."
    )

    librarians = Profile.objects.filter(userRole=1)
    for librarian in librarians:
        if librarian != collection.creator.user:
            Message.objects.create(
                sender=request.user,
                recipient=librarian.user,
                content=f"{request.user.username} has requested access to the collection '{collection.name}'."
            )

    messages.success(request, "Access request sent successfully!")
    return redirect('collection_detail', collection_id=collection.id)
@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'edit_profile.html', {'form': form})

@login_required
def submit_item_review(request, item_uuid):
    item = get_object_or_404(Item, uuid=item_uuid)
    user_review = ItemReview.objects.filter(reviewer=request.user, item=item).first()
    next_url = request.GET.get('next', None)
    
    if request.method == 'POST':
        form = ItemReviewForm(request.POST)
        if form.is_valid():
            rating = int(form.cleaned_data['rating'])
            if user_review:
                user_review.rating = rating
                user_review.review_text = form.cleaned_data['review_text']
                user_review.save()
            else:
                ItemReview.objects.create(
                    reviewer=request.user,
                    item=item,
                    rating=rating,
                    review_text=form.cleaned_data['review_text']
                )
            if next_url:
                return redirect(next_url)
            return redirect('item_detail', uuid=item_uuid)
    else:
        initial_data = {}
        if user_review:
            initial_data = {
                'rating': str(user_review.rating), 
                'review_text': user_review.review_text
            }
        form = ItemReviewForm(initial=initial_data)
    
    return render(request, 'submit_review.html', {
        'form': form,
        'item': item,
        'user_review': user_review,
        'review_type': 'item',
        'next_url': next_url
    })

@login_required
def submit_user_review(request, user_id):
    reviewed_user = get_object_or_404(User, id=user_id)
    user_review = UserReview.objects.filter(reviewer=request.user, reviewed_user=reviewed_user).first()
    next_url = request.GET.get('next', None)
    
    if request.method == 'POST':
        form = UserReviewForm(request.POST)
        if form.is_valid():
            rating = int(form.cleaned_data['rating'])
            if user_review:
                user_review.rating = rating
                user_review.review_text = form.cleaned_data['review_text']
                user_review.save()
            else:
                UserReview.objects.create(
                    reviewer=request.user,
                    reviewed_user=reviewed_user,
                    rating=rating,
                    review_text=form.cleaned_data['review_text']
                )
            if next_url:
                return redirect(next_url)
            return redirect('user_profile', user_id=user_id)
    else:
        initial_data = {}
        if user_review:
            initial_data = {
                'rating': str(user_review.rating),  
                'review_text': user_review.review_text
            }
        form = UserReviewForm(initial=initial_data)
    
    return render(request, 'submit_review.html', {
        'form': form,
        'reviewed_user': reviewed_user,
        'user_review': user_review,
        'review_type': 'user',
        'next_url': next_url
    })

@login_required
def delete_item(request, uuid):
    item = get_object_or_404(Item, uuid=uuid)
    
    if request.user.profile.userRole != 1 or item.owner != request.user:
        return HttpResponseForbidden("You do not have permission to delete this item.")
    
    if request.method == 'POST':
        item.delete()
        return home_page_router(request)
    
    return HttpResponseForbidden("Invalid request method.")

@login_required
def edit_item(request, uuid):
    item = get_object_or_404(Item, uuid=uuid)

    if request.user.profile.userRole != 1 or item.owner != request.user:
        return HttpResponseForbidden("You do not have permission to edit this item.")
    if item.status != Item.STATUS_AVAILABLE:
        return HttpResponseForbidden("You can only edit available items.")

    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()  

            for img_id in request.POST.getlist('delete_image_ids'):
                item.images.filter(id=img_id).delete()

            for f in request.FILES.getlist('images'):
                img = ItemImage.objects.create(image=f)
                item.images.add(img)

            messages.success(request, "Item updated successfully!")
            return redirect('item_detail', uuid=item.uuid)
    else:
        form = ItemForm(instance=item)

    return render(request, 'edit_item.html', {
        'form': form,
        'item': item,
    })

@login_required
def user_reviews(request):
    item_reviews = ItemReview.objects.filter(reviewer=request.user).order_by('-created_at')
    user_reviews = UserReview.objects.filter(reviewer=request.user).order_by('-created_at')
    
    return render(request, 'user_reviews.html', {
        'item_reviews': item_reviews,
        'user_reviews': user_reviews
    })

@login_required
def delete_collection(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    if collection.creator != request.user.profile and request.user.profile.userRole != 1:
        return HttpResponseForbidden("You do not have permission to delete this collection.")
    if request.method == "POST":
        collection.delete()
        return redirect('collections')
    return render(request, "confirm_delete_collection.html", {"collection": collection})

@login_required
def delete_item_review(request, review_id):
    review = get_object_or_404(ItemReview, id=review_id)
    if review.reviewer != request.user:
        return HttpResponseForbidden("You do not have permission to delete this review.")
    
    next_url = request.GET.get('next')
    review.delete()
    messages.success(request, 'Review deleted successfully.')
    
    if next_url:
        return redirect(next_url)
    return redirect('item_detail', uuid=review.item.uuid)

@login_required
def delete_user_review(request, review_id):
    review = get_object_or_404(UserReview, id=review_id)
    if review.reviewer != request.user:
        return HttpResponseForbidden("You do not have permission to delete this review.")
    
    next_url = request.GET.get('next')
    reviewed_user_id = review.reviewed_user.id
    review.delete()
    messages.success(request, 'Review deleted successfully.')
    
    if next_url:
        return redirect(next_url)
    return redirect('user_profile', user_id=reviewed_user_id)

@login_required
def librarian_requests(request):
    if request.user.profile.userRole != 1:
        return HttpResponseForbidden("You are not authorized to view this page.")
    
    requested_items = Item.objects.filter(status='requested')
    collection_access_requests = CollectionAccessRequest.objects.filter(status='pending')
    
    context = {
        'requested_items': requested_items,
        'collection_access_requests': collection_access_requests,
    }
    return render(request, "librarian_requests.html", context)

@login_required
def process_collection_access_request(request):
    if request.user.profile.userRole != 1:
        return HttpResponseForbidden("You are not authorized to process collection access requests.")
    
    try:
        request_id = request.POST['request']
        access_request = CollectionAccessRequest.objects.get(id=request_id)
    except (KeyError, CollectionAccessRequest.DoesNotExist):
        return HttpResponseRedirect(reverse('librarian_requests'))
    
    if 'action' in request.POST:
        if request.POST['action'] == 'approve':
            access_request.status = 'approved'
            access_request.collection.access.add(access_request.user.profile)
            Message.objects.create(
                sender=request.user,
                recipient=access_request.user,
                content=f"Your request to access the collection '{access_request.collection.name}' has been approved."
            )
        elif request.POST['action'] == 'deny':
            access_request.status = 'denied'
            Message.objects.create(
                sender=request.user,
                recipient=access_request.user,
                content=f"Your request to access the collection '{access_request.collection.name}' has been denied."
            )
        access_request.save()
    
    return HttpResponseRedirect(reverse('librarian_requests'))