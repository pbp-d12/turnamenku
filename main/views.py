from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView as DjangoPasswordChangeView
from django.urls import reverse_lazy, reverse
import datetime
from django.db.models import Sum
from teams.models import Team
from predictions.models import Prediction
from tournaments.models import Tournament, Match 
from forums.models import Thread 
from predictions.models import Prediction 
from django.db.models import Count, F 
from django.utils import timezone


def home_view(request):
    now_datetime = timezone.now()
    now_date = now_datetime.date()

    ongoing_tournaments = Tournament.objects.filter(
        start_date__lte=now_date,
        end_date__gte=now_date
    ).order_by('-start_date')[:3]

    upcoming_matches_for_prediction = Match.objects.filter(
        match_date__gte=now_datetime, 
        home_score__isnull=True,      
        away_score__isnull=True
    ).select_related('tournament', 'home_team', 'away_team').order_by('match_date')[:3]

    recent_threads = Thread.objects.select_related('tournament', 'author')\
        .annotate(post_count=Count('posts'))\
        .order_by('-created_at')[:3]

    top_predictors = Prediction.objects.values('user__username')\
        .annotate(total_points=Sum('points_awarded'))\
        .filter(total_points__gt=0)\
        .order_by('-total_points')[:3]

    user_rank = None
    user_teams = None
    if request.user.is_authenticated:
        user_total_points = Prediction.objects.filter(user=request.user)\
            .aggregate(total=Sum('points_awarded'))['total'] or 0

        higher_ranked_users = Prediction.objects.values('user')\
            .annotate(total_points=Sum('points_awarded'))\
            .filter(total_points__gt=user_total_points)\
            .count()
        user_rank = higher_ranked_users + 1

        user_teams = request.user.teams.all()[:2] 

    context = {
        'ongoing_tournaments': ongoing_tournaments,
        'upcoming_matches': upcoming_matches_for_prediction,
        'recent_threads': recent_threads,
        'top_predictors': top_predictors,
        'user_rank': user_rank, 
        'user_total_points': user_total_points if request.user.is_authenticated else 0,
        'user_teams': user_teams, 
    }
    return render(request, 'main/home.html', context)

from .forms import (
    UserRegisterForm,
    CustomLoginForm as LoginForm,
    UserUpdateForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm
)
from .models import Profile


def is_superuser(user): return user.is_superuser

def register_view(request):
    if request.user.is_authenticated:
        return redirect('main:profile', username=request.user.username)
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({"status": "success", "message": "Registrasi berhasil! Kamu akan diarahkan ke halaman login."}, status=201)
        else:
            errors_dict = form.errors.get_json_data(escape_html=True)
            return JsonResponse({"status": "error", "message": "Registrasi gagal.", "errors": errors_dict}, status=400)
    form = UserRegisterForm()
    context = {'form': form}
    return render(request, 'main/register.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('main:home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                response_data = {"status": "success", "message": "Login berhasil!", "redirect_url": reverse(
                    "main:home")}
                response = JsonResponse(response_data, status=200)
                # response.set_cookie('last_login', str(datetime.datetime.now()))
                return response
        else:
            return JsonResponse({"status": "error", "message": "Nama pengguna atau kata sandi salah."}, status=401)
    form = LoginForm()
    context = {'form': form}
    return render(request, 'main/login.html', context)


@login_required
def logout_view(request):
    logout(request)
    response_data = {"status": "success", "message": "Kamu berhasil logout.",
                     "redirect_url": reverse('main:login')}
    response = JsonResponse(response_data)
    response.delete_cookie('last_login')
    return response


def profile_view(request, username):
    try:
        profile_user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, f"Pengguna '{username}' tidak ditemukan.")
        return redirect('main:home')
    try:
        profile = profile_user.profile
    except Profile.DoesNotExist:
        messages.error(
            request, f"Pengguna '{username}' tidak memiliki profil terkait.")
        return redirect('main:home')
    user_teams = Team.objects.filter(members=profile_user)
    user_predictions = Prediction.objects.filter(
        user=profile_user
    ).select_related('match', 'predicted_winner').order_by('-created_at')

    total_points = user_predictions.aggregate(Sum('points_awarded'))[
        'points_awarded__sum'] or 0

    context = {
        'profile_user': profile_user,
        'profile': profile,
        'user_teams': user_teams,
        'user_predictions': user_predictions,
        'total_prediction_points': total_points,
    }
    return render(request, 'main/profile.html', context)


@login_required
def edit_my_profile_view(request):
    target_user = request.user
    if request.method == 'POST':
        if 'username' in request.POST and request.POST['username'] != target_user.username:
            return JsonResponse({"status": "error", "message": "Nama pengguna tidak bisa diubah."}, status=400)

        u_form = UserUpdateForm(
            request.POST, instance=target_user, user=request.user)
        if 'username' in u_form.changed_data:
            return JsonResponse({"status": "error", "message": "Nama pengguna tidak bisa diubah."}, status=400)

        p_form = ProfileUpdateForm(
            request.POST, instance=target_user.profile, request=request)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return JsonResponse({"status": "success", "message": "Profil kamu berhasil diperbarui!", "redirect_url": reverse('main:profile', kwargs={'username': target_user.username})}, status=200)
        else:
            errors_dict = {}
            u_form_errors = u_form.errors.get_json_data(escape_html=True)
            p_form_errors = p_form.errors.get_json_data(escape_html=True)
            errors_dict.update(u_form_errors)
            errors_dict.update(p_form_errors)
            return JsonResponse({"status": "error", "message": "Gagal memperbarui profil.", "errors": errors_dict}, status=400)
    else:
        u_form = UserUpdateForm(instance=target_user, user=request.user)
        p_form = ProfileUpdateForm(
            instance=target_user.profile, request=request)
    context = {'u_form': u_form, 'p_form': p_form, 'editing_user': target_user}
    return render(request, 'main/edit_profile.html', context)


@user_passes_test(is_superuser)
def edit_user_profile_view(request, username):
    try:
        target_user = User.objects.get(username=username)
        target_profile = target_user.profile
    except (User.DoesNotExist, Profile.DoesNotExist):
        messages.error(
            request, f"Pengguna '{username}' atau profilnya tidak ditemukan.")
        return redirect('main:home')

    if request.method == 'POST':
        u_form = UserUpdateForm(
            request.POST, instance=target_user, user=request.user)
        p_form = ProfileUpdateForm(
            request.POST, instance=target_profile, request=request)

        if not u_form.is_valid():
            print("!!! DEBUG u_form errors:", u_form.errors)
        if not p_form.is_valid():
            print("!!! DEBUG p_form errors:", p_form.errors)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return JsonResponse({"status": "success", "message": f"Profil '{username}' berhasil diperbarui oleh Admin!", "redirect_url": reverse('main:profile', kwargs={'username': target_user.username})}, status=200)
        else:
            errors_dict = {}
            u_form_errors = u_form.errors.get_json_data(escape_html=True)
            p_form_errors = p_form.errors.get_json_data(escape_html=True)
            errors_dict.update(u_form_errors)
            errors_dict.update(p_form_errors)
            return JsonResponse({"status": "error", "message": f"Gagal memperbarui profil '{username}'.", "errors": errors_dict}, status=400)
    else:
        u_form = UserUpdateForm(instance=target_user, user=request.user)
        p_form = ProfileUpdateForm(instance=target_profile, request=request)
    context = {'u_form': u_form, 'p_form': p_form, 'editing_user': target_user}
    return render(request, 'main/edit_profile.html', context)


class CustomPasswordChangeView(LoginRequiredMixin, DjangoPasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'main/change_password.html'
    success_url = reverse_lazy('main:password_change_done')

    def form_valid(self, form): user = form.save(); update_session_auth_hash(self.request, user); return JsonResponse(
        {"status": "success", "message": "Kata sandi Anda berhasil diubah!", "redirect_url": reverse('main:profile', kwargs={'username': self.request.user.username})}, status=200)
    def form_invalid(self, form): errors_dict = form.errors.get_json_data(escape_html=True); return JsonResponse(
        {"status": "error", "message": "Gagal mengubah kata sandi.", "errors": errors_dict}, status=400)

    def get(self, request, *args, **kwargs): form = self.get_form(
    ); return render(request, self.template_name, {'form': form})
