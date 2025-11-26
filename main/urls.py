from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import CustomPasswordChangeView
from django.contrib.auth.decorators import login_required
from .views import login_flutter, register_flutter, logout_flutter, show_home_json

app_name = 'main'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.edit_my_profile_view, name='edit_my_profile'),
    # URL BARU untuk admin edit profil user lain (DENGAN username)
    path('profile/edit/<str:username>/',
         views.edit_user_profile_view, name='edit_user_profile'),
    path('profile/u/<str:username>/', views.profile_view, name='profile'),
    path('auth/login/', login_flutter, name='login_flutter'),
    path('auth/register/', register_flutter, name='register_flutter'),
    path('auth/logout/', logout_flutter, name='logout_flutter'),
    path('change_password/',
         CustomPasswordChangeView.as_view(),
         name='change_password'),
    path('api/home/', show_home_json, name='show_home_json'),
]
