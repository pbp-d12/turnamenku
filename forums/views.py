from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from forums.models import Thread, Post
from tournaments.models import Tournament
import json

def forum_threads(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    
    threads = tournament.threads.order_by('-created_at')
    
    context = {
        'threads': threads,
        'tournament': tournament
    }
    return render(request, 'forums/forum_threads.html', context)

@login_required
def thread_posts(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        content = data.get('content', '')

        if content:
            post = Post.objects.create(
                thread=thread,
                user=request.user, 
                content=content
            )
            
            return JsonResponse({
                'status': 'success',
                'username': post.user.username,
                'content': post.content,
                'created_at': post.created_at.strftime('%d %b %Y, %H:%M')
            }, status=201)
        
        return JsonResponse({'status': 'error', 'message': 'Content is empty'}, status=400)

    posts = thread.posts.order_by('created_at')
    
    context = {
        'posts': posts,
        'thread': thread
    }
    return render(request, 'forums/thread_posts.html', context)