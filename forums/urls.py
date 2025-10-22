from django.urls import path
from . import views

app_name = 'forums'

urlpatterns = [
    path('<int:tournament_id>/', views.forum_threads, name='forum_threads'),
    path('thread/<uuid:thread_id>/', views.thread_posts, name='thread_posts'),
]