from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from forums.models import Thread, Post
from tournaments.models import Tournament
from django.db.models import Count, Q
import json
from django.core.paginator import Paginator

@login_required
def create_thread(request, tournament_id):
    """
    Membuat thread baru di forum turnamen tertentu.
    Handles both standard form posts and AJAX/JSON requests.
    """
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        title = None
        body = None
        
        if is_ajax and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body)
                title = data.get('title')
                body = data.get('body')
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        else:
            title = request.POST.get('title')
            body = request.POST.get('body')

        if title and body:
            thread = Thread.objects.create(
                tournament=tournament,
                title=title,
                author=request.user
            )

            Post.objects.create(
                thread=thread,
                author=request.user,
                body=body
            )
            
            if is_ajax:
                thread_url = reverse('forums:thread_posts', args=[thread.id])
                return JsonResponse({'success': True, 'thread_url': thread_url})
            else:
                return redirect('forums:thread_posts', thread_id=thread.id)
        else:
            error = "Judul dan isi thread tidak boleh kosong."
            if is_ajax:
                return JsonResponse({'success': False, 'error': error}, status=400)
            else:
                return render(request, 'forums/create_threads.html', {'tournament': tournament, 'error': error})

    return render(request, 'forums/create_threads.html', {'tournament': tournament})


def forum_index(request):
    """
    Menampilkan daftar semua turnamen yang memiliki forum.
    """
    return render(request, 'forums/forum_index.html')


def forum_threads(request, tournament_id):
    """
    Menampilkan *halaman* untuk thread turnamen.
    Data thread sekarang akan dimuat oleh AJAX.
    """
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    context = {
        'tournament': tournament
    }
    return render(request, 'forums/forum_threads.html', context)

def get_tournament_threads(request, tournament_id):
    """
    AJAX endpoint to get paginated threads for a specific tournament.
    """
    try:
        tournament = get_object_or_404(Tournament, pk=tournament_id)
        
        query = request.GET.get('q', '').strip()
        page_number = request.GET.get('page', 1)
        base_queryset = tournament.threads.select_related('author').annotate(
            post_count=Count('posts') 
        ).order_by('-created_at')
        if query:
            base_queryset = base_queryset.filter(title__icontains=query)

        paginator = Paginator(base_queryset, 15)
        page_obj = paginator.get_page(page_number)

        threads_data = []
        for thread in page_obj.object_list:
            threads_data.append({
                'id': thread.id,
                'title': thread.title,
                'url': reverse('forums:thread_posts', args=[thread.id]),
                'author_username': thread.author.username if thread.author else 'Unknown',
                'created_date': thread.created_at.strftime('%d %b %Y'),
                'created_time': thread.created_at.strftime('%H:%M'),
                'reply_count': thread.post_count - 1
            })
        
        return JsonResponse({
            'threads': threads_data,
            'pagination': {
                'current_page': page_obj.number,
                'has_next': page_obj.has_next(),
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
            }
        })

    except Exception as e:
        print(f"Error in get_tournament_threads: {e}")
        return JsonResponse({'error': 'Terjadi kesalahan pada server.'}, status=500)

def thread_posts(request, thread_id):
    """
    Menampilkan post dalam thread dan menangani penambahan post baru.
    """
    thread = get_object_or_404(Thread, pk=thread_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        if not request.user.is_authenticated:
            if is_ajax:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            else:
                return redirect('login')

        body_content = None

        if is_ajax and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body)
                body_content = data.get('body')
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
        else:
            body_content = request.POST.get('body')
        
        if body_content:
            post = Post.objects.create(
                thread=thread,
                author=request.user,
                body=body_content
            )
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'username': post.author.username,
                    'body': post.body,
                    'created_at': post.created_at.strftime('%d %b %Y, %H:%M')
                }, status=201) 
            else:
                return redirect('forums:thread_posts', thread_id=thread.id)
        else:
            if is_ajax:
                return JsonResponse({'error': 'Content is required'}, status=400)
            else:
                return redirect('forums:thread_posts', thread_id=thread.id)
    
    posts = thread.posts.all().order_by('created_at') 
    context = {'thread': thread, 'posts': posts}
    return render(request, 'forums/thread_posts.html', context)


def search_tournaments(request):
    """
    Searches, paginates, and returns tournaments as JSON
    for the forum_index page's AJAX script.
    """
    try:
        query = request.GET.get('q', '').strip()
        page_number = request.GET.get('page', 1)

        base_queryset = Tournament.objects.select_related('organizer').annotate(
            participant_count=Count('participants', distinct=True)
        ).order_by('name')

        if query:
            base_queryset = base_queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )

        paginator = Paginator(base_queryset, 10) 
        page_obj = paginator.get_page(page_number)

        tournaments_data = []
        for tournament in page_obj.object_list:
            tournaments_data.append({
                'id': tournament.id,
                'name': tournament.name,
                'description': tournament.description or "Tidak ada deskripsi",
                'participant_count': tournament.participant_count,
                'url': reverse('forums:forum_threads', args=[tournament.id]),
                'start_date': tournament.start_date.strftime('%d %b %Y') if tournament.start_date else 'Belum ditentukan',
                'end_date': tournament.end_date.strftime('%d %b %Y') if tournament.end_date else 'Belum ditentukan',
                'organizer_username': tournament.organizer.username if tournament.organizer else 'Tidak diketahui'
            })

        return JsonResponse({
            'tournaments': tournaments_data,
            'pagination': {
                'current_page': page_obj.number,
                'has_next': page_obj.has_next(),
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
            }
        })
    
    except Exception as e:
        print(f"Error in search_tournaments: {e}") 
        return JsonResponse({'error': 'Terjadi kesalahan pada server.'}, status=500)