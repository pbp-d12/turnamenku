from django.urls import path
from . import views

app_name = 'forums'

urlpatterns = [
    path('', views.forum_index, name='forum_index'),
    path('search/', views.search_tournaments, name='search_tournaments'),
    path('tournament/<int:tournament_id>/', views.forum_threads, name='forum_threads'),
    path('tournament/<int:tournament_id>/threads/', views.get_tournament_threads, name='get_tournament_threads'),
    path('tournament/<int:tournament_id>/create/', views.create_thread, name='create_thread'),
    path('thread/<int:thread_id>/', views.thread_posts, name='thread_posts'),
    path('thread/<int:thread_id>/edit/', views.edit_thread, name='edit_thread'),
    path('thread/<int:thread_id>/delete/', views.delete_thread, name='delete_thread'),
    path('post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('api/tournament/<int:tournament_id>/threads/', views.api_get_tournament_threads, name='api_get_tournament_threads'),
    path('api/tournament/<int:tournament_id>/create-thread/', views.api_create_thread, name='api_create_thread'),
    path('api/thread/<int:thread_id>/reply/', views.api_reply_to_thread, name='api_reply_to_thread'),
    path('api/thread/<int:thread_id>/posts/', views.api_thread_posts, name='api_thread_posts'),
    path('api/post/<int:post_id>/edit/', views.api_edit_post, name='api_edit_post'),
    path('api/post/<int:post_id>/delete/', views.api_delete_post, name='api_delete_post'),
    path('api/thread/<int:thread_id>/delete/', views.api_delete_thread, name='api_delete_thread'),
]