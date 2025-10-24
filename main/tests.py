from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from .models import Profile
from .forms import (
    UserRegisterForm, CustomLoginForm, UserUpdateForm,
    ProfileUpdateForm, CustomPasswordChangeForm
)
from .views import (
    home_view, register_view, login_view, logout_view, profile_view,
    edit_my_profile_view, edit_user_profile_view, CustomPasswordChangeView
)
from teams.models import Team
from predictions.models import Prediction
# Asumsi nama model Match di tournaments
from tournaments.models import Tournament, Match


class BaseTestCase(TestCase):
    def setUp(self):
        """Setup user biasa dan superuser untuk pengujian."""
        self.client = Client()
        self.user_password = 'testpassword123'

        # User Biasa (Pemain)
        self.user_pemain = User.objects.create_user(
            username='pemaintest',
            email='pemain@test.com',
            password=self.user_password
        )
        # Profile dibuat oleh signal, kita cek/ambil saja
        self.profile_pemain = Profile.objects.get(user=self.user_pemain)
        # Pastikan role default (jika signal benar)
        self.assertEqual(self.profile_pemain.role, 'PEMAIN')

        # User Biasa (Penyelenggara) - Buat manual untuk tes role
        self.user_penyelenggara = User.objects.create_user(
            username='panitiatest',
            email='panitia@test.com',
            password=self.user_password
        )
        self.profile_penyelenggara, created = Profile.objects.get_or_create(
            user=self.user_penyelenggara,
            defaults={'role': 'PENYELENGGARA'}  # Set role manual jika perlu
        )
        if not created:  # Jika sudah dibuat signal, update role
            self.profile_penyelenggara.role = 'PENYELENGGARA'
            self.profile_penyelenggara.save()

        # Superuser (Admin)
        self.admin_user = User.objects.create_superuser(
            username='admintest',
            email='admin@test.com',
            password=self.user_password
        )
        # Profile dibuat oleh signal, kita cek/ambil saja
        self.profile_admin = Profile.objects.get(user=self.admin_user)
        # Pastikan role ADMIN (jika signal benar)
        self.assertEqual(self.profile_admin.role, 'ADMIN')

        # Data dummy untuk profile view (jika diperlukan)
        # self.team1 = Team.objects.create(name='Tim A')
        # self.team1.members.add(self.user_pemain)
        # self.tournament1 = Tournament.objects.create(name='Turnamen Coba')
        # self.match1 = Match.objects.create(tournament=self.tournament1, team1=self.team1, team2=Team.objects.create(name='Tim B'))
        # self.prediction1 = Prediction.objects.create(user=self.user_pemain, match=self.match1, predicted_winner=self.team1)


class ProfileModelTest(BaseTestCase):
    def test_profile_creation_signal(self):
        """Tes apakah signal membuat Profile saat User dibuat."""
        user = User.objects.create_user(
            username='signaltest', password='woihitam')
        self.assertTrue(Profile.objects.filter(user=user).exists())
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.role, 'PEMAIN')  # Cek role default

    def test_superuser_profile_creation_signal(self):
        """Tes apakah signal membuat Profile ADMIN saat Superuser dibuat."""
        admin = User.objects.create_superuser(
            username='signaladmin', password='woihitam')
        self.assertTrue(Profile.objects.filter(user=admin).exists())
        profile = Profile.objects.get(user=admin)
        self.assertEqual(profile.role, 'ADMIN')

    def test_profile_picture_url_or_default(self):
        """Tes property profile_picture_url_or_default."""
        # Tanpa URL
        self.assertTrue(
            'default_avatar.png' in self.profile_pemain.profile_picture_url_or_default)

        # Dengan URL
        test_url = "https://example.com/test.jpg"
        self.profile_pemain.profile_picture = test_url
        self.profile_pemain.save()
        self.assertEqual(
            self.profile_pemain.profile_picture_url_or_default, test_url)


class UserRegisterFormTest(TestCase):
    def test_valid_form(self):
        """Tes form registrasi dengan data valid."""
        data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'role': 'PEMAIN',
            'password1': 'validpassword123',
            'password2': 'validpassword123',
        }
        form = UserRegisterForm(data=data)
        if not form.is_valid():
            print("\n[DEBUG] test_valid_form errors:", form.errors.as_json())
        self.assertTrue(form.is_valid())

    def test_invalid_password_mismatch(self):
        """Tes form registrasi dengan password tidak cocok."""
        data = {
            'username': 'newuser', 'email': 'new@test.com', 'role': 'PEMAIN',
            'password1': 'validpassword123',  # <-- Tambah field ini
            'password2': 'WRONGpassword123'  # <-- Ganti nama field ini
        }
        form = UserRegisterForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue(
            'password2' in form.errors or '__all__' in form.errors)

    def test_invalid_username_taken(self):
        """Tes form registrasi dengan username sudah ada."""
        User.objects.create_user(username='existinguser', password='woihitam')
        data = {
            'username': 'existinguser', 'email': 'new@test.com', 'role': 'PEMAIN',
            'password1': 'woihitam',
            'password2': 'woihitam'
        }
        form = UserRegisterForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_register_form_save_creates_profile(self):
        """Tes apakah form.save() membuat User dan memicu pembuatan Profile."""
        data = {
            'username': 'saveuser', 'email': 'save@test.com', 'role': 'PENYELENGGARA',
            'password1': 'woihitam',
            'password2': 'woihitam'
        }
        form = UserRegisterForm(data=data)
        if not form.is_valid():
            print("\n[DEBUG] test_register_form_save errors:",
                  form.errors.as_json())
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(User.objects.filter(username='saveuser').exists())
        self.assertTrue(Profile.objects.filter(user=user).exists())
        profile = Profile.objects.get(user=user)


class LoginFormTest(BaseTestCase):
    def test_valid_login(self):
        """Tes form login dengan kredensial valid."""
        data = {'username': self.user_pemain.username,
                'password': self.user_password}
        # LoginForm butuh request object, kita bisa pakai None atau mock jika perlu
        form = CustomLoginForm(request=None, data=data)
        self.assertTrue(form.is_valid())

    def test_invalid_login(self):
        """Tes form login dengan password salah."""
        data = {'username': self.user_pemain.username,
                'password': 'wrongpassword'}
        form = CustomLoginForm(request=None, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)  # Error login biasanya non-field

# Tambahkan test untuk UserUpdateForm, ProfileUpdateForm, CustomPasswordChangeForm
# Fokus pada validasi field unik (jika ada), dan logic __init__ (misal disable field)
# Untuk __init__ yang butuh 'request' atau 'user', mungkin lebih mudah dites via View Test


class MainURLTests(TestCase):
    def test_urls_resolve_correct_views(self):
        """Tes apakah URL name me-resolve ke view function/class yang benar."""
        self.assertEqual(resolve(reverse('main:home')).func, home_view)
        self.assertEqual(resolve(reverse('main:register')).func, register_view)
        self.assertEqual(resolve(reverse('main:login')).func, login_view)
        self.assertEqual(resolve(reverse('main:logout')).func, logout_view)
        # Untuk Class-Based View, cek .view_class
        self.assertEqual(resolve(reverse('main:change_password')
                                 ).func.view_class, CustomPasswordChangeView)
        # Tes URL dengan argumen
        self.assertEqual(resolve(reverse('main:profile', kwargs={
                         'username': 'test'})).func, profile_view)
        self.assertEqual(
            resolve(reverse('main:edit_my_profile')).func, edit_my_profile_view)
        self.assertEqual(resolve(reverse('main:edit_user_profile', kwargs={
                         'username': 'test'})).func, edit_user_profile_view)


class MainViewTests(BaseTestCase):

    # --- Home View ---
    def test_home_view_get(self):
        """Tes akses GET ke home view."""
        response = self.client.get(reverse('main:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/home.html')

    # --- Register View ---
    def test_register_view_get(self):
        """Tes akses GET ke register view (user belum login)."""
        response = self.client.get(reverse('main:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/register.html')
        self.assertIsInstance(response.context['form'], UserRegisterForm)

    def test_register_view_get_authenticated(self):
        """Tes akses GET ke register view (user sudah login) -> redirect."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        response = self.client.get(reverse('main:register'))
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertRedirects(response, reverse('main:profile', kwargs={
                             'username': self.user_pemain.username}))

    def test_register_view_post_success(self):
        """Tes POST valid ke register view -> JSON success."""
        data = {
            'username': 'newreg', 'email': 'newreg@test.com', 'role': 'PEMAIN',
            'password1': self.user_password,
            'password2': self.user_password
        }
        response = self.client.post(reverse('main:register'), data)
        if response.status_code != 201:
            try:
                print(
                    "\n[DEBUG] test_register_view_post_success response:", response.json())
            except:
                print("\n[DEBUG] test_register_view_post_success response (not json):",
                      response.content.decode())
        self.assertEqual(response.status_code, 201)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        self.assertTrue(User.objects.filter(username='newreg').exists())
        self.assertTrue(Profile.objects.filter(
            user__username='newreg').exists())

    def test_register_view_post_fail(self):
        """Tes POST invalid ke register view -> JSON error."""
        data = {  # Password tidak cocok
            'username': 'newregfail', 'email': 'newregfail@test.com', 'role': 'PEMAIN',
            'password1': 'woihitam1',
            'password2': 'woihitam2'
        }
        response = self.client.post(reverse('main:register'), data)
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('errors', json_response)
        self.assertFalse(User.objects.filter(username='newregfail').exists())

    # --- Login View ---
    def test_login_view_get(self):
        """Tes akses GET ke login view."""
        response = self.client.get(reverse('main:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/login.html')
        self.assertIsInstance(response.context['form'], CustomLoginForm)

    def test_login_view_get_authenticated(self):
        """Tes akses GET ke login (sudah login) -> redirect home."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        response = self.client.get(reverse('main:login'))
        # Perhatikan: view kamu redirect ke 'main:home', bukan profile
        # Sesuaikan assertRedirects jika redirect-nya beda
        self.assertEqual(response.status_code, 302)
        # Jika redirect ke home:
        self.assertRedirects(response, reverse('main:home'))
        # Jika seharusnya ke profile:
        # self.assertRedirects(response, reverse('main:profile', kwargs={'username': self.user_pemain.username}))

    def test_register_view_post_success(self):
        """Tes POST valid ke register view -> JSON success."""
        data = {
            'username': 'newreg', 'email': 'newreg@test.com', 'role': 'PEMAIN',
            'password1': self.user_password,
            'password2': self.user_password
        }
        response = self.client.post(reverse('main:register'), data)
        self.assertEqual(response.status_code, 201)  # Harusnya 201 Created
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        self.assertTrue(User.objects.filter(username='newreg').exists())
        self.assertTrue(Profile.objects.filter(
            user__username='newreg').exists())

    def test_register_view_post_fail(self):
        """Tes POST invalid ke register view -> JSON error."""
        data = {  # Password tidak cocok
            'username': 'newregfail', 'email': 'newregfail@test.com', 'role': 'PEMAIN',
            'password1': 'woihitam1',
            'password2': 'woihitam2'
        }
        response = self.client.post(reverse('main:register'), data)
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('errors', json_response)
        self.assertFalse(User.objects.filter(username='newregfail').exists())

    # --- Logout View ---
    def test_logout_view_requires_login(self):
        """Tes akses logout tanpa login -> redirect."""
        response = self.client.post(
            reverse('main:logout'))  # Logout harus POST
        self.assertEqual(response.status_code, 302)  # Redirect ke login page
        self.assertTrue(response.url.startswith(
            reverse('main:login')))  # Cek URL redirect default

    def test_logout_view_post(self):
        """Tes POST ke logout -> JSON success & clear session."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        self.assertTrue('_auth_user_id' in self.client.session)
        response = self.client.post(reverse('main:logout'))
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        self.assertEqual(json_response['redirect_url'], reverse('main:login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    # --- Profile View ---

    def test_profile_view_get_exists(self):
        """Tes akses GET ke profile user yang ada."""
        response = self.client.get(reverse('main:profile', kwargs={
                                   'username': self.user_pemain.username}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/profile.html')
        self.assertEqual(response.context['profile_user'], self.user_pemain)
        # Cek context lain jika perlu (teams, predictions)
        self.assertIn('user_teams', response.context)
        self.assertIn('user_predictions', response.context)
        self.assertIn('total_prediction_points', response.context)

    def test_profile_view_get_not_exists(self):
        """Tes akses GET ke profile user yang tidak ada -> redirect home."""
        response = self.client.get(
            reverse('main:profile', kwargs={'username': 'nouser'}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('main:home'))

    # Tambahkan tes untuk user ada tapi profile tidak ada (jika memungkinkan)

    # --- Edit My Profile View ---
    def test_edit_my_profile_get_requires_login(self):
        """Tes akses GET edit profile tanpa login -> redirect."""
        response = self.client.get(reverse('main:edit_my_profile'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('main:login')))

    def test_edit_my_profile_get(self):
        """Tes akses GET edit profile (sudah login)."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        response = self.client.get(reverse('main:edit_my_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/edit_profile.html')
        self.assertIsInstance(response.context['u_form'], UserUpdateForm)
        self.assertIsInstance(response.context['p_form'], ProfileUpdateForm)
        # Cek apakah username disabled (karena user biasa edit diri sendiri)
        self.assertTrue(response.context['u_form'].fields['username'].disabled)

    def test_edit_my_profile_post_success(self):
        """Tes POST valid ke edit profile -> JSON success & data updated."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        new_email = "newemail@test.com"
        new_bio = "Ini bio baru."
        new_role = 'PENYELENGGARA'  # User biasa boleh ganti role ini
        data = {
            'username': self.user_pemain.username,  # Harus dikirim meski disabled
            'email': new_email,
            'role': new_role,
            'bio': new_bio,
            'profile_picture': 'https://newpic.com/img.jpg'
        }
        response = self.client.post(reverse('main:edit_my_profile'), data)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        # Cek data di database
        self.user_pemain.refresh_from_db()
        self.profile_pemain.refresh_from_db()
        self.assertEqual(self.user_pemain.email, new_email)
        self.assertEqual(self.profile_pemain.bio, new_bio)
        self.assertEqual(self.profile_pemain.role, new_role)
        self.assertEqual(self.profile_pemain.profile_picture,
                         data['profile_picture'])

    def test_edit_my_profile_post_fail_username_change(self):
        """Tes POST mencoba ganti username -> JSON error."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        data = {
            'username': 'usernamebaru',  # Mencoba ganti username
            'email': self.user_pemain.email,
            'role': self.profile_pemain.role, 'bio': '', 'profile_picture': ''
        }
        response = self.client.post(reverse('main:edit_my_profile'), data)
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertEqual(json_response['message'],
                         "Nama pengguna tidak bisa diubah.")

    # Tambahkan tes untuk POST invalid lainnya (misal email tidak valid)

    # --- Edit User Profile View (Admin) ---
    def test_edit_user_profile_get_requires_superuser(self):
        """Tes akses GET edit user lain oleh user biasa -> redirect."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        response = self.client.get(reverse('main:edit_user_profile', kwargs={
                                   'username': self.admin_user.username}))
        # Redirect ke login page (default user_passes_test)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('main:login')))

    def test_edit_user_profile_get_by_admin(self):
        """Tes akses GET edit user lain oleh admin."""
        self.client.login(username=self.admin_user.username,
                          password=self.user_password)
        response = self.client.get(reverse('main:edit_user_profile', kwargs={
                                   'username': self.user_pemain.username}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/edit_profile.html')
        # Cek apakah username TIDAK disabled (karena admin edit user biasa)
        self.assertFalse(
            response.context['u_form'].fields['username'].disabled)

    def test_edit_admin_profile_get_by_admin(self):
        """Tes akses GET edit profil admin lain oleh admin -> username disabled."""
        other_admin = User.objects.create_superuser(
            'otheradmin', 'oa@test.com', 'woihitam')
        self.client.login(username=self.admin_user.username,
                          password=self.user_password)
        response = self.client.get(reverse('main:edit_user_profile', kwargs={
                                   'username': other_admin.username}))
        self.assertEqual(response.status_code, 200)
        # Cek username disabled (karena admin edit admin lain)
        self.assertTrue(response.context['u_form'].fields['username'].disabled)
        # Cek role disabled
        self.assertTrue(response.context['p_form'].fields['role'].disabled)

    def test_edit_user_profile_post_success_by_admin(self):
        """Tes POST valid ke edit user lain oleh admin -> JSON success & data updated."""
        self.client.login(username=self.admin_user.username,
                          password=self.user_password)
        new_username_for_pemain = "pemainbaru"
        new_role_for_pemain = "ADMIN"  # Admin boleh ganti role jadi apa saja
        data = {
            'username': new_username_for_pemain,  # Admin boleh ganti
            'email': self.user_pemain.email,
            'role': new_role_for_pemain,
            'bio': 'Bio diubah admin', 'profile_picture': ''
        }
        response = self.client.post(reverse('main:edit_user_profile', kwargs={
                                    'username': self.user_pemain.username}), data)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        # Cek data di database
        self.user_pemain.refresh_from_db()
        self.profile_pemain.refresh_from_db()
        self.assertEqual(self.user_pemain.username, new_username_for_pemain)
        self.assertEqual(self.profile_pemain.role, new_role_for_pemain)
        self.assertEqual(self.profile_pemain.bio, data['bio'])

    # --- Change Password View ---

    def test_change_password_get_requires_login(self):
        """Tes akses GET ganti password tanpa login -> redirect."""
        response = self.client.get(reverse('main:change_password'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('main:login')))

    def test_change_password_get(self):
        """Tes akses GET ganti password (sudah login)."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        response = self.client.get(reverse('main:change_password'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/change_password.html')
        self.assertIsInstance(
            response.context['form'], CustomPasswordChangeForm)

    def test_change_password_post_success(self):
        """Tes POST valid ke ganti password -> JSON success."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        new_password = "newpassword456"
        data = {
            'old_password': self.user_password,
            'new_password1': new_password,
            'new_password2': new_password,
        }
        response = self.client.post(reverse('main:change_password'), data)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        # Cek apakah bisa login dengan password baru
        self.client.logout()
        login_success = self.client.login(
            username=self.user_pemain.username, password=new_password)
        self.assertTrue(login_success)

    def test_change_password_post_fail(self):
        """Tes POST invalid ke ganti password -> JSON error."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        data = {  # Password lama salah
            'old_password': 'wrongoldpassword',
            'password1': 'newwoihitam',
            'password2': 'newwoihitam',
        }
        response = self.client.post(reverse('main:change_password'), data)
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('errors', json_response)
        # Pastikan password tidak berubah
        self.client.logout()
        login_fail = self.client.login(
            username=self.user_pemain.username, password='newwoihitam')
        self.assertFalse(login_fail)
        login_success = self.client.login(
            username=self.user_pemain.username, password=self.user_password)
        self.assertTrue(login_success)

    def test_profile_view_get_user_no_profile(self):
        """Tes akses GET ke profile user yang ada TAPI tidak punya profile -> redirect home."""
        # Buat user baru tanpa memicu signal (atau hapus profile-nya)
        user_no_profile = User.objects.create_user(
            username='noprofile', password='pw')
        # Hapus profile-nya jika signal otomatis membuat
        if hasattr(user_no_profile, 'profile'):
            user_no_profile.profile.delete()

        response = self.client.get(
            reverse('main:profile', kwargs={'username': 'noprofile'}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('main:home'))
        # Cek apakah messages.error dipanggil (opsional tapi bagus)
        # messages = list(get_messages(response.wsgi_request))
        # self.assertEqual(len(messages), 1)
        # self.assertEqual(messages[0].level, messages.ERROR)

    def test_edit_my_profile_post_invalid_form(self):
        """Tes POST invalid (misal email salah) ke edit profile -> JSON error."""
        self.client.login(username=self.user_pemain.username,
                          password=self.user_password)
        data = {
            'username': self.user_pemain.username,
            'email': 'ini-bukan-email',  # <-- Data tidak valid
            'role': 'PEMAIN',
            'bio': 'Bio tes',
            'profile_picture': ''
        }
        response = self.client.post(reverse('main:edit_my_profile'), data)
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('errors', json_response)
        # Pastikan errornya di field email
        self.assertIn('email', json_response['errors'])

    def test_edit_user_profile_get_not_exists_by_admin(self):
        """Tes akses GET edit user yang tidak ada oleh admin -> redirect home."""
        self.client.login(username=self.admin_user.username,
                          password=self.user_password)
        response = self.client.get(
            reverse('main:edit_user_profile', kwargs={'username': 'nouser'}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('main:home'))

    def test_edit_user_profile_post_invalid_form_by_admin(self):
        """Tes POST invalid ke edit user lain oleh admin -> JSON error."""
        self.client.login(username=self.admin_user.username,
                          password=self.user_password)
        data = {
            'username': 'pemaintest',
            'email': 'ini-bukan-email',  # <-- Data tidak valid
            'role': 'PEMAIN',
            'bio': '', 'profile_picture': ''
        }
        response = self.client.post(reverse('main:edit_user_profile', kwargs={
                                    'username': self.user_pemain.username}), data)
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('errors', json_response)
        self.assertIn('email', json_response['errors'])

# ==============================================
# Jalankan test & coverage
# ==============================================
# Di terminal:
# coverage run manage.py test main
# coverage report -m
# coverage html # (Untuk lihat report detail di browser)
