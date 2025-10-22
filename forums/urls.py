from django.urls import path
from . import views

app_name = 'forums'

urlpatterns = [
    path('', views.forum_index, name='forum_index'),
    path('<int:tournament_id>/', views.forum_threads, name='forum_threads'),
    path('<int:tournament_id>/create/', views.create_thread, name='create_thread'),
    path('thread/<int:thread_id>/', views.thread_posts, name='thread_posts'),
]