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
]