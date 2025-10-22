from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from forums.models import Thread, Post
from tournaments.models import Tournament
import json

@login_required
def create_thread(request, tournament_id):
    """
    Membuat thread baru di forum turnamen tertentu.
    """
    tournament = get_object_or_404(Tournament, pk=tournament_id)

    if request.method == 'POST':
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
            return redirect('forums:thread_posts', thread_id=thread.id)
        else:
            error = "Judul dan isi thread tidak boleh kosong."
            return render(request, 'forums/create_thread.html', {'tournament': tournament, 'error': error})
    
    return render(request, 'forums/create_threads.html', {'tournament': tournament})


def forum_index(request):
    """
    Menampilkan daftar semua turnamen yang memiliki forum.
    """
    tournaments = Tournament.objects.all().order_by('name')
    context = {
        'tournaments': tournaments
    }
    return render(request, 'forums/forum_index.html', context)


def forum_threads(request, tournament_id):
    """
    Menampilkan daftar semua thread untuk satu turnamen spesifik.
    """
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    
    threads = tournament.threads.order_by('-created_at')
    
    context = {
        'threads': threads,
        'tournament': tournament
    }
    return render(request, 'forums/forum_threads.html', context)


def thread_posts(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    posts = thread.posts.all()
    
    if request.method == 'POST':
        body_content = request.POST.get('body')
        
        if body_content:
            post = Post.objects.create(
                thread=thread,
                author=request.user,
                body=body_content
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'username': request.user.username,
                    'content': post.body,
                    'created_at': post.created_at.strftime('%d %b %Y, %H:%M')
                })
            else:
                return redirect('forums:thread_posts', thread_id=thread.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Content is required'}, status=400)
            else:
                return redirect('forums:thread_posts', thread_id=thread.id)
    
    context = {'thread': thread, 'posts': posts}
    return render(request, 'forums/thread_posts.html', context)