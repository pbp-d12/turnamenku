from .forms import (
    UserRegisterForm,
    CustomLoginForm as LoginForm,
    UserUpdateForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm
)
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Profile
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
from django.views.decorators.http import require_GET, require_POST
from django.middleware.csrf import get_token


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


@csrf_exempt  # Gunakan ini jika error CSRF masih membandel saat testing awal
def login_flutter(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)  # <--- PENTING: Membuat session cookie
                return JsonResponse({
                    "status": True,
                    "message": "Berhasil login!",
                    "username": username,
                }, status=200)
            else:
                return JsonResponse({
                    "status": False,
                    "message": "Username atau password salah.",
                }, status=401)
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": f"Error processing request: {str(e)}",
            }, status=500)

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


@csrf_exempt
def register_flutter(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            password_confirmation = data.get('password_confirmation')
            email = data.get('email')
            role = data.get('role')

            if password != password_confirmation:
                return JsonResponse({"status": False, "message": "Password tidak sama."}, status=400)

            if not email or not role:
                return JsonResponse({"status": False, "message": "Email dan peran akun wajib diisi."}, status=400)

            if User.objects.filter(username=username).exists():
                return JsonResponse({"status": False, "message": "Username sudah digunakan."}, status=409)

            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
            )
            user.save()

            user.profile.role = role
            user.profile.save()

            return JsonResponse({"status": True, "message": "Akun berhasil dibuat!"}, status=201)
        except Exception as e:
            return JsonResponse({"status": False, "message": f"Terjadi kesalahan server: {str(e)}"}, status=500)

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


@csrf_exempt
def logout_flutter(request):
    logout(request)
    return JsonResponse({
        "status": True,
        "message": "Berhasil logout!",
    }, status=200)


@csrf_exempt
@require_GET
def show_home_json(request):
    now_datetime = timezone.now()
    now_date = now_datetime.date()

    ongoing_tournaments = Tournament.objects.filter(
        start_date__lte=now_date,
        end_date__gte=now_date
    ).order_by('-start_date')[:3]

    ongoing_list = []
    for t in ongoing_tournaments:
        ongoing_list.append({
            'id': t.pk,
            'name': t.name,
            'end_date': t.end_date.strftime("%d %b %Y")
        })

    upcoming_matches = Match.objects.filter(
        match_date__gte=now_datetime,
        home_score__isnull=True,
        away_score__isnull=True
    ).select_related('tournament', 'home_team', 'away_team').order_by('match_date')[:3]

    match_list = []
    for m in upcoming_matches:
        match_list.append({
            'home_team': m.home_team.name,
            'away_team': m.away_team.name,
            'tournament_name': m.tournament.name,
            'date': m.match_date.strftime("%d %b, %H:%M")
        })

    recent_threads = Thread.objects.select_related('tournament', 'author')\
        .annotate(post_count=Count('posts'))\
        .order_by('-created_at')[:3]

    thread_list = []
    for th in recent_threads:
        thread_list.append({
            'id': th.pk,
            'title': th.title,
            'author': th.author.username,
            'tournament': th.tournament.name,
            'reply_count': max(0, th.post_count - 1)
        })

    top_predictors = Prediction.objects.values('user__username')\
        .annotate(total_points=Sum('points_awarded'))\
        .filter(total_points__gt=0)\
        .order_by('-total_points')[:3]

    predictor_list = list(top_predictors)

    user_data = None
    if request.user.is_authenticated:
        user_total_points = Prediction.objects.filter(user=request.user)\
            .aggregate(total=Sum('points_awarded'))['total'] or 0

        higher_ranked_users = Prediction.objects.values('user')\
            .annotate(total_points=Sum('points_awarded'))\
            .filter(total_points__gt=user_total_points)\
            .count()
        user_rank = higher_ranked_users + 1

        my_teams = request.user.teams.all()[:2]
        team_list = []
        for team in my_teams:
            team_list.append({
                'name': team.name,
                'logo': team.logo if team.logo else "https://img.icons8.com/?size=100&id=uMMzE4KzgxCO&format=png&color=000000"
            })

        try:
            profile = request.user.profile
            role = profile.role
            profile_pic = profile.profile_picture if profile.profile_picture else ""
        except:
            role = "Member"
            profile_pic = ""

        user_data = {
            'username': request.user.username,
            'email': request.user.email,
            'role': role,
            'profile_picture': profile_pic,
            'rank': user_rank,
            'total_points': user_total_points,
            'teams': team_list
        }

    stats = {
        'tournaments_count': Tournament.objects.filter(start_date__lte=now_date, end_date__gte=now_date).count(),
        'matches_count': Match.objects.filter(match_date__gte=now_datetime).count(),
        'threads_count': Thread.objects.count(),
        'predictors_count': Prediction.objects.values('user').distinct().count()
    }

    return JsonResponse({
        'status': True,
        'ongoing_tournaments': ongoing_list,
        'upcoming_matches': match_list,
        'recent_threads': thread_list,
        'top_predictors': predictor_list,
        'user_data': user_data,
        'stats': stats
    })


@csrf_exempt
def show_profile_json(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': False, 'message': 'Belum login'}, status=401)

    user = request.user
    try:
        profile = user.profile

        data = {
            'status': True,
            'username': user.username,
            'email': user.email,
            'role': profile.role,
            'bio': profile.bio if profile.bio else "-",
            'profile_picture': profile.profile_picture if profile.profile_picture else "",
            'date_joined': user.date_joined.strftime("%d %B %Y"),
            'last_login': user.last_login.strftime("%d %B %Y") if user.last_login else "-",
        }
        return JsonResponse(data, status=200)
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)}, status=500)


def get_profile_json(request):
    target_id = request.GET.get('id')

    if target_id:
        target_user = get_object_or_404(User, pk=target_id)
    else:
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Not logged in'}, status=401)
        target_user = request.user

    try:
        profile = target_user.profile
        role = profile.role
    except:
        profile = None
        role = 'PENGGUNA'

    can_edit = False
    if request.user.is_authenticated:
        is_self = request.user.pk == target_user.pk
        is_admin = False
        try:
            is_admin = request.user.profile.role == 'ADMIN'
        except:
            pass

        if is_self or is_admin:
            can_edit = True

    data = {
        'id': target_user.id,
        'username': target_user.username,
        'name': profile.name if profile else '',
        'email': profile.email if profile else '',
        'role': role,
        'profile_picture': profile.profile_picture if profile else None,
        'can_edit': can_edit,
    }
    return JsonResponse({'status': 'success', 'data': data})


@csrf_exempt
@require_POST
def update_profile_flutter(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
        target_id = data.get('id')

        if target_id:
            target_user = get_object_or_404(User, pk=target_id)
        else:
            target_user = request.user

        requester_role = getattr(request.user.profile, 'role', 'PENGGUNA')
        target_role = getattr(target_user.profile, 'role', 'PENGGUNA')

        is_self = (request.user.pk == target_user.pk)
        is_admin = (requester_role == 'ADMIN')

        if not (is_self or is_admin):
            return JsonResponse({'status': 'error', 'message': 'Anda tidak punya izin edit profil ini.'}, status=403)

        new_username = data.get('username')
        new_name = data.get('name')
        new_email = data.get('email')

        if new_username and new_username != target_user.username:
            if target_role == 'ADMIN':
                return JsonResponse({'status': 'error', 'message': 'Username Admin bersifat PERMANEN dan tidak bisa diubah.'}, status=403)

            if User.objects.filter(username=new_username).exclude(pk=target_user.pk).exists():
                return JsonResponse({'status': 'error', 'message': f'Username "{new_username}" sudah dipakai orang lain.'}, status=400)

            target_user.username = new_username

        if new_email:
            target_user.email = new_email

        if new_name:
            target_user.profile.name = new_name
            target_user.profile.save()

        target_user.save()

        return JsonResponse({'status': 'success', 'message': 'Profil berhasil diperbarui!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
