from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.urls import reverse
from forums.models import Thread, Post
from tournaments.models import Tournament
from django.db.models import Count, Q, F
from django.db.models.functions import Coalesce
import json
from django.core.paginator import Paginator
from django.contrib import messages
from .forms import ThreadCreateForm, PostReplyForm, ThreadEditForm, PostEditForm
from datetime import datetime
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone 


def can_edit_thread(user, thread):
    """Check if user can edit thread"""
    if not user.is_authenticated:
        return False

    user_role = None
    try:
        if hasattr(user, 'profile'):
            user_role = user.profile.role
    except:
        pass
    
    return (user == thread.author or
            user_role == 'ADMIN' or
            user == thread.tournament.organizer or
            user.is_superuser)

def can_edit_post(user, post):
    """Check if user can edit post"""
    if not user.is_authenticated:
        return False
        
    user_role = None
    try:
        if hasattr(user, 'profile'):
            user_role = user.profile.role
    except:
        pass
    
    return (user == post.author or
            user_role == 'ADMIN' or
            user == post.thread.tournament.organizer or
            user.is_superuser)

def can_delete_thread(user, thread):
    """Check if user can delete thread"""
    if not user.is_authenticated:
        return False
        
    user_role = None
    try:
        if hasattr(user, 'profile'):
            user_role = user.profile.role
    except:
        pass
    
    return (user == thread.author or
            user_role == 'ADMIN' or
            user == thread.tournament.organizer or
            user.is_superuser)

def can_delete_post(user, post):
    """Check if user can delete post"""
    if not user.is_authenticated:
        return False
        
    user_role = None
    try:
        if hasattr(user, 'profile'):
            user_role = user.profile.role
    except:
        pass
    
    return (user == post.author or
            user_role == 'ADMIN' or
            user == post.thread.tournament.organizer or
            user.is_superuser)


@login_required
def create_thread(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST' and is_ajax:
        form = ThreadCreateForm(request.POST)
        if form.is_valid():
            try:
                title = form.cleaned_data['title']
                body = form.cleaned_data['body']
                image_url = form.cleaned_data.get('image')
                image_url = None if not image_url else image_url
                thread = Thread.objects.create(tournament=tournament, title=title, author=request.user)
                Post.objects.create(thread=thread, author=request.user, body=body, image=image_url, parent=None)
                thread_url = reverse('forums:thread_posts', args=[thread.id])
                return JsonResponse({'success': True, 'thread_url': thread_url}, status=201)
            except Exception as e:
                print(f"Error in create_thread: {e}")
                return JsonResponse({'success': False, 'error': 'Terjadi kesalahan pada server.'}, status=500)
        else:
            error_dict = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'error': 'Validation failed', 'errors': error_dict}, status=400)
    else:
        form = ThreadCreateForm()
    context = {'form': form, 'tournament': tournament}
    return render(request, 'forums/create_threads.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def edit_thread(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)

    if not can_edit_thread(request.user, thread):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)
        return HttpResponseForbidden("You don't have permission to edit this thread.")

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST' and is_ajax:
        form = ThreadEditForm(request.POST, instance=thread)
        if form.is_valid():
            thread = form.save()

            thread_data = {
                'id': thread.id,
                'title': thread.title,
                'url': reverse('forums:thread_posts', args=[thread.id]),
                'author_username': thread.author.username if thread.author else 'Unknown',
                'created_date': timezone.localtime(thread.created_at).strftime('%d %b %Y'), 
                'created_time': timezone.localtime(thread.created_at).strftime('%H:%M'), 
                'reply_count': max(0, thread.posts.filter(is_deleted=False).count() - 1),
                'can_edit': True,
                'can_delete': can_delete_thread(request.user, thread),
            }

            return JsonResponse({'success': True, 'thread': thread_data})
        else:
            error_dict = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'error': 'Validation failed', 'errors': error_dict}, status=400)

    if is_ajax:
        form = ThreadEditForm(instance=thread) 
        return JsonResponse({
            'success': True,
            'form_data': {
                'title': thread.title
            }
        })
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method for non-AJAX GET.'}, status=405)


@login_required
@require_http_methods(["GET", "POST"])
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id, is_deleted=False)

    if not can_edit_post(request.user, post):
         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)
         return HttpResponseForbidden("You don't have permission to edit this post.")

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST' and is_ajax:
        form = PostEditForm(request.POST, instance=post)
        if form.is_valid():
            remove_image = request.POST.get('remove_image') == 'on'
            post_instance = form.save(commit=False) 
            if remove_image:
                post_instance.image = None
            post_instance.save()
            form.save_m2m()
            reply_count = Post.objects.filter(parent=post_instance, is_deleted=False).count()

            post_data = {
                "id": post_instance.pk,
                "author_username": post_instance.author.username,
                "body": post_instance.body, 
                "body_raw": post_instance.body, 
                "created_at": timezone.localtime(post_instance.created_at).strftime('%d %b %Y, %H:%M'),
                "image_url": post_instance.image, 
                "parent_id": post_instance.parent.pk if post_instance.parent else None,
                "is_thread_author": post_instance.author == post_instance.thread.author,
                "reply_count": reply_count,
                "is_edited": post_instance.is_edited,
                "can_edit": True, 
                "can_delete": can_delete_post(request.user, post_instance)
            }

            return JsonResponse({'success': True, 'post': post_data})
        else:
            error_dict = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'error': 'Validation failed', 'errors': error_dict}, status=400)

    if is_ajax:
        return JsonResponse({
            'success': True,
            'form_data': {
                'body': post.body,
                'image_url': post.image 
            }
        })
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method for non-AJAX GET.'}, status=405)


@login_required
@require_POST
def delete_thread(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)

    if not can_delete_thread(request.user, thread):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)
        return HttpResponseForbidden("You don't have permission to delete this thread.")

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    thread.is_deleted = True
    thread.save()

    if is_ajax:
        return JsonResponse({'success': True, 'redirect_url': reverse('forums:forum_threads', args=[thread.tournament.id])})
    else:
        messages.success(request, "Thread berhasil dihapus.")
        return redirect('forums:forum_threads', tournament_id=thread.tournament.id)


@login_required
@require_POST
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if not can_delete_post(request.user, post):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)
        return HttpResponseForbidden("You don't have permission to delete this post.")

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    post.is_deleted = True
    post.save()

    if is_ajax:
        return JsonResponse({'success': True})
    else:
        messages.success(request, "Post berhasil dihapus.")
        return redirect('forums:thread_posts', thread_id=post.thread_id)


def forum_index(request):
    return render(request, 'forums/forum_index.html')


def forum_threads(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    context = {'tournament': tournament}
    return render(request, 'forums/forum_threads.html', context)


def get_tournament_threads(request, tournament_id):
    try:
        tournament = get_object_or_404(Tournament, pk=tournament_id)

        query = request.GET.get('q', '').strip()
        author_query = request.GET.get('author', '').strip()
        sort_param = request.GET.get('sort', '-created_at')
        page_number = request.GET.get('page', 1)

        base_queryset = tournament.threads.filter(is_deleted=False).select_related('author').annotate(
             reply_count_agg=Coalesce(Count('posts', filter=Q(posts__is_deleted=False)), 0) - 1
        )

        filters = Q()
        if query:
            filters &= Q(title__icontains=query)
        if author_query:
            filters &= Q(author__username__icontains=author_query)

        base_queryset = base_queryset.filter(filters)

        valid_sort_fields = {
            'created_at': 'created_at',
            'popularity': 'reply_count_agg',
            'title': 'title',
            'author': 'author__username'
        }
        sort_key = sort_param.lstrip('-')
        sort_direction = '-' if sort_param.startswith('-') else ''

        order_field_name = valid_sort_fields.get(sort_key, 'created_at') 
        final_order_field = sort_direction + order_field_name

        if 'reply_count_agg' in final_order_field:
            if final_order_field.startswith('-'):
                 base_queryset = base_queryset.order_by(F('reply_count_agg').desc(nulls_last=True), '-created_at') 
            else:
                 base_queryset = base_queryset.order_by(F('reply_count_agg').asc(nulls_first=True), 'created_at') 
        else:
             base_queryset = base_queryset.order_by(final_order_field)

        paginator = Paginator(base_queryset, 15)
        page_obj = paginator.get_page(page_number)

        threads_data = []
        for thread in page_obj.object_list:
            reply_count = max(0, thread.reply_count_agg)
            threads_data.append({
                'id': thread.id, 'title': thread.title,
                'url': reverse('forums:thread_posts', args=[thread.id]),
                'author_username': thread.author.username if thread.author else 'Unknown',
                'created_date': timezone.localtime(thread.created_at).strftime('%d %b %Y'),
                'created_time': timezone.localtime(thread.created_at).strftime('%H:%M'),
                'reply_count': reply_count,
                'can_edit': can_edit_thread(request.user, thread),
                'can_delete': can_delete_thread(request.user, thread),
            })

        return JsonResponse({ 'threads': threads_data, 'pagination': {
                'current_page': page_obj.number, 'has_next': page_obj.has_next(),
                'total_pages': paginator.num_pages, 'total_count': paginator.count,
            }})

    except Exception as e:
        print(f"Error in get_tournament_threads: {e}")
        return JsonResponse({'error': 'Terjadi kesalahan pada server.'}, status=500)


def thread_posts(request, thread_id):
    thread = get_object_or_404(Thread.objects.select_related('author', 'tournament'), pk=thread_id)

    if thread.is_deleted:
        raise Http404("Thread tidak ditemukan.")

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST' and is_ajax:
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required', 'login_url': reverse('main:login')}, status=401)
        form = PostReplyForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.thread = thread
            post.author = request.user
            parent_id = request.POST.get('parent_id')
            parent_post = None
            if parent_id:
                try:
                    parent_post = Post.objects.get(pk=parent_id, thread=thread, is_deleted=False)
                    post.parent = parent_post
                except Post.DoesNotExist:
                    post.parent = None
            else:
                 post.parent = None
            post.save() 
            depth = 0
            temp_parent = parent_post
            while temp_parent:
                depth += 1
                temp_parent = temp_parent.parent

            response_data = {
                'success': True,
                'post': {
                    'id': post.pk,
                    'author_username': post.author.username,
                    'body': post.body,
                    'body_raw': post.body,
                    'created_at': timezone.localtime(post.created_at).strftime('%d %b %Y, %H:%M'),
                    'image_url': post.image,
                    'parent_id': post.parent.pk if post.parent else None,
                    'is_thread_author': post.author == thread.author,
                    'reply_count': 0, 
                    'is_edited': post.is_edited,
                    'can_edit': can_edit_post(request.user, post),
                    'can_delete': can_delete_post(request.user, post),
                    'depth': depth,
                }
            }
            return JsonResponse(response_data, status=201)
        else:
            error_dict = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'error': 'Validation failed', 'errors': error_dict}, status=400)

    all_posts = thread.posts.filter(is_deleted=False).select_related('author').order_by('created_at')

    posts_json_data = []

    reply_counts_query = Post.objects.filter(thread=thread, parent__isnull=False, is_deleted=False)\
                           .values('parent_id').annotate(count=Count('id'))
    reply_count_map = {item['parent_id']: item['count'] for item in reply_counts_query}

    for post in all_posts:
        posts_json_data.append({
            "id": post.pk,
            "author_username": post.author.username,
            "body": post.body,
            "body_raw": post.body, 
            "created_at": timezone.localtime(post.created_at).strftime('%d %b %Y, %H:%M'),
            "image_url": post.image, 
            "parent_id": post.parent.pk if post.parent else None,
            "is_thread_author": post.author == thread.author,
            "reply_count": reply_count_map.get(post.pk, 0),
            "is_edited": post.is_edited,
            "can_edit": can_edit_post(request.user, post),
            "can_delete": can_delete_post(request.user, post),
        })

    reply_count_total = max(0, all_posts.count() - 1)
    reply_form = PostReplyForm() 
    context = {
        'thread': thread,
        'posts_json': json.dumps(posts_json_data),
        'reply_count': reply_count_total,
        'reply_form': reply_form,
        'can_edit_thread': can_edit_thread(request.user, thread),
        'can_delete_thread': can_delete_thread(request.user, thread),
    }
    return render(request, 'forums/thread_posts.html', context)

def search_tournaments(request):
    try:
        query = request.GET.get('q', '').strip()
        organizer_query = request.GET.get('organizer', '').strip()
        start_date_after_str = request.GET.get('start_date_after', '').strip()
        end_date_before_str = request.GET.get('end_date_before', '').strip()
        participant_str = request.GET.get('participants', '').strip()
        sort_param = request.GET.get('sort', 'name') 
        primary_sort_field = request.GET.get('primary_sort', 'name')
        page_number = request.GET.get('page', 1)

        base_queryset = Tournament.objects.select_related('organizer').annotate(
            participant_count=Count('participants', distinct=True)
        )

        filters = Q()
        active_filter_keys = []

        if query:
            filters &= (Q(name__icontains=query) | Q(description__icontains=query))
        if organizer_query:
            filters &= Q(organizer__username__icontains=organizer_query)
            active_filter_keys.append('organizer')
        if start_date_after_str:
            try:
                start_date_after_obj = datetime.strptime(start_date_after_str, '%Y-%m-%d').date()
                filters &= Q(start_date__gte=start_date_after_obj)
                if 'start_date' not in active_filter_keys: active_filter_keys.append('start_date')
            except ValueError: pass
        if end_date_before_str:
            try:
                end_date_before_obj = datetime.strptime(end_date_before_str, '%Y-%m-%d').date()
                filters &= Q(end_date__lte=end_date_before_obj)
                if 'start_date' not in active_filter_keys: active_filter_keys.append('start_date')
            except ValueError: pass
        if participant_str:
            try:
                participant_count_int = int(participant_str)
                filters &= Q(participant_count=participant_count_int)
                active_filter_keys.append('participants')
            except ValueError: pass

        base_queryset = base_queryset.filter(filters)

        filter_count = len(active_filter_keys)

        sort_direction_prefix = '-' if sort_param.startswith('-') else ''
        sort_key_actual = 'name' 

        if filter_count > 1:
             sort_key_actual = 'name' 
        elif filter_count == 1:
             sort_key_actual = primary_sort_field 
        else: 
             sort_key_from_param = sort_param.lstrip('-')
             if sort_key_from_param in ['name', 'start_date', 'participants', 'organizer']:
                  sort_key_actual = sort_key_from_param
             else:
                  sort_key_actual = 'name' 

        field_mapping = {
            'name': 'name',
            'start_date': 'start_date',
            'participants': 'participant_count',
            'organizer': 'organizer__username'
        }

        order_field_name = field_mapping.get(sort_key_actual, 'name')
        final_order_field = sort_direction_prefix + order_field_name

        if 'participant_count' in final_order_field:
             if final_order_field.startswith('-'):
                 base_queryset = base_queryset.order_by(F('participant_count').desc(nulls_last=True), 'name') 
             else:
                 base_queryset = base_queryset.order_by(F('participant_count').asc(nulls_first=True), 'name') 
        else:
             base_queryset = base_queryset.order_by(final_order_field)

        paginator = Paginator(base_queryset, 10)
        page_obj = paginator.get_page(page_number)

        tournaments_data = []
        for tournament in page_obj.object_list:
            tournaments_data.append({
                'id': tournament.id, 'name': tournament.name,
                'description': tournament.description or "Tidak ada deskripsi",
                'participant_count': tournament.participant_count,
                'url': reverse('forums:forum_threads', args=[tournament.id]),
                'start_date': tournament.start_date.strftime('%d %b %Y') if tournament.start_date else 'Belum ditentukan',
                'end_date': tournament.end_date.strftime('%d %b %Y') if tournament.end_date else 'Belum ditentukan',
                'organizer_username': tournament.organizer.username if tournament.organizer else 'Tidak diketahui'
            })

        return JsonResponse({ 'tournaments': tournaments_data, 'pagination': {
                'current_page': page_obj.number, 'has_next': page_obj.has_next(),
                'total_pages': paginator.num_pages, 'total_count': paginator.count,
            }})

    except Exception as e:
        print(f"Error in search_tournaments: {e}")
        return JsonResponse({'error': 'Terjadi kesalahan pada server.'}, status=500)