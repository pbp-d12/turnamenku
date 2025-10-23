from .forms import (
    UserRegisterForm,
    LoginForm,
    UserUpdateForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm
)
from .models import Profile
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse, reverse_lazy
import datetime
from django.contrib.auth.views import PasswordChangeView as DjangoPasswordChangeView


def is_superuser(user):
    return user.is_superuser


def home_view(request):
    context = {}
    return render(request, 'main/home.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('main:profile', username=request.user.username)

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({
                "status": "success",
                "message": "Registrasi berhasil! Kamu akan diarahkan ke halaman login."
            }, status=201)
        else:
            errors_dict = form.errors.get_json_data()
            return JsonResponse({
                "status": "error",
                "message": "Registrasi gagal.",
                "errors": errors_dict
            }, status=400)

    form = UserRegisterForm()
    context = {'form': form}
    return render(request, 'main/register.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('main:home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        next_url = request.POST.get('next') or request.GET.get('next')

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                redirect_target = next_url or reverse("main:home")
                response_data = {
                    "status": "success",
                    "message": "Login berhasil!",
                    "redirect_url": redirect_target
                }
                response = JsonResponse(response_data, status=200)
                response.set_cookie('last_login', str(datetime.datetime.now()))
                return response

        return JsonResponse({
            "status": "error",
            "message": "Username atau password salah."
        }, status=401)

    form = LoginForm()
    context = {
        'form': form,
        'next': request.GET.get('next', '')
    }
    return render(request, 'main/login.html', context)


@login_required
def logout_view(request):
    logout(request)
    response_data = {
        "status": "success",
        "message": "Kamu berhasil logout.",
        "redirect_url": reverse('main:home')
    }
    response = JsonResponse(response_data)
    response.delete_cookie('last_login')
    return response


def profile_view(request, username):
    """
    View untuk menampilkan halaman profil publik.
    Redirects to home if the user doesn't exist OR has no profile.
    """
    try:
        profile_user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, f"User '{username}' not found.")
        return redirect('main:home')

    try:
        profile = profile_user.profile
    except Profile.DoesNotExist:
        messages.error(
            request, f"User '{username}' does not have an associated profile.")
        return redirect('main:home')

    context = {
        'profile_user': profile_user,
        'profile': profile,
    }
    return render(request, 'main/profile.html', context)


@login_required
def edit_my_profile_view(request):
    """
    Menangani user mengedit profilnya sendiri via AJAX.
    (Ini adalah view 'edit_profile_view' lama, ganti nama saja)
    """
    target_user = request.user  # Targetnya selalu user yang login

    if request.method == 'POST':
        # Kita tidak izinkan user biasa ganti username
        u_form = UserUpdateForm(request.POST, instance=target_user)
        # Email bisa diganti
        if 'username' in u_form.changed_data:  # Cegah manipulasi HTML
            return JsonResponse({"status": "error", "message": "Nama pengguna tidak bisa diubah."}, status=400)

        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=target_user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return JsonResponse({
                "status": "success",
                "message": "Profil kamu berhasil diperbarui!",
                "redirect_url": reverse('main:profile', kwargs={'username': target_user.username})
            }, status=200)
        else:
            errors_dict = {}
            # ... (logic kumpulkan error tetap sama) ...
            u_form_errors = u_form.errors.get_json_data(escape_html=True)
            p_form_errors = p_form.errors.get_json_data(escape_html=True)
            errors_dict.update(u_form_errors)
            errors_dict.update(p_form_errors)
            return JsonResponse({
                "status": "error",
                "message": "Gagal memperbarui profil.",
                "errors": errors_dict
            }, status=400)
    else:
        # Tampilkan form untuk user yang login
        u_form = UserUpdateForm(instance=target_user)
        p_form = ProfileUpdateForm(instance=target_user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'editing_user': target_user  # Kirim info user yg diedit ke template
    }
    return render(request, 'main/edit_profile.html', context)


# --- View BARU KHUSUS ADMIN mengedit profil ORANG LAIN ---
@user_passes_test(is_superuser)  # Hanya superuser yang bisa akses
def edit_user_profile_view(request, username):
    """
    Menangani ADMIN mengedit profil user lain via AJAX.
    """
    try:
        target_user = User.objects.get(
            username=username)  # User yang mau diedit
        target_profile = target_user.profile
    except (User.DoesNotExist, Profile.DoesNotExist):
        messages.error(
            request, f"Pengguna '{username}' atau profilnya tidak ditemukan.")
        # Redirect jika user/profile target tidak ada
        return redirect('main:home')

    if request.method == 'POST':
        # Admin BOLEH ganti username user lain
        u_form = UserUpdateForm(request.POST, instance=target_user)
        # Aktifkan kembali field username khusus untuk view ini
        u_form.fields['username'].disabled = False
        # Info tambahan
        u_form.fields['username'].help_text = "Admin dapat mengubah nama pengguna."

        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=target_profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return JsonResponse({
                "status": "success",
                "message": f"Profil '{username}' berhasil diperbarui oleh Admin!",
                # Redirect kembali ke profil user yang diedit
                "redirect_url": reverse('main:profile', kwargs={'username': target_user.username})
            }, status=200)
        else:
            errors_dict = {}
            # ... (logic kumpulkan error tetap sama) ...
            u_form_errors = u_form.errors.get_json_data(escape_html=True)
            p_form_errors = p_form.errors.get_json_data(escape_html=True)
            errors_dict.update(u_form_errors)
            errors_dict.update(p_form_errors)
            return JsonResponse({
                "status": "error",
                "message": f"Gagal memperbarui profil '{username}'.",
                "errors": errors_dict
            }, status=400)
    else:
        # Tampilkan form untuk user TARGET
        u_form = UserUpdateForm(instance=target_user)
        # Aktifkan field username untuk admin
        u_form.fields['username'].disabled = False
        u_form.fields['username'].help_text = "Admin dapat mengubah nama pengguna."

        p_form = ProfileUpdateForm(instance=target_profile)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'editing_user': target_user  # Kirim info user yg diedit ke template
    }
    # Kita bisa pakai template yang sama, tapi judulnya perlu disesuaikan
    return render(request, 'main/edit_profile.html', context)


class CustomPasswordChangeView(LoginRequiredMixin, DjangoPasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'main/change_password.html'
    success_url = reverse_lazy('main:password_change_done')

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)

        return JsonResponse({
            "status": "success",
            "message": "Password Anda berhasil diubah!",
            "redirect_url": reverse('main:profile', kwargs={'username': self.request.user.username})
        }, status=200)

    def form_invalid(self, form):
        errors_dict = form.errors.get_json_data()

        return JsonResponse({
            "status": "error",
            "message": "Gagal mengubah password.",
            "errors": errors_dict
        }, status=400)

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        return render(request, self.template_name, {'form': form})
