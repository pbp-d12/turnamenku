from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
import json
from main.models import Profile
from teams.models import Team
from .models import Tournament, Match
from .forms import TournamentForm


def create_user_with_profile(username, password, role):
    """Membuat user beserta profile-nya."""
    user = User.objects.create_user(username=username, password=password)
    Profile.objects.update_or_create(
        user=user,
        defaults={'role': role}
    )
    return user





#testcases
class TournamentModelTest(TestCase):
    """Pengujian untuk model Tournament."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user_with_profile("organizer_test", "password123", "PENYELENGGARA")
        cls.tournament = Tournament.objects.create(
            name="Test Tournament",
            organizer=cls.user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=7)
        )

    def test_tournament_creation(self):
        """Test membuat instance Tournament."""
        self.assertIsInstance(self.tournament, Tournament)
        self.assertEqual(self.tournament.name, "Test Tournament")
        self.assertEqual(self.tournament.organizer, self.user)

    def test_tournament_str_representation(self):
        """Test representasi string model Tournament."""
        self.assertEqual(str(self.tournament), "Test Tournament")

class MatchModelTest(TestCase):
    """Pengujian untuk model Match."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user_with_profile("organizer_match", "password123", "PENYELENGGARA")
        cls.team1 = Team.objects.create(name="Team Alpha")
        cls.team2 = Team.objects.create(name="Team Beta")
        cls.tournament = Tournament.objects.create(
            name="Match Test Tournament",
            organizer=cls.user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=7)
        )
        cls.match = Match.objects.create(
            tournament=cls.tournament,
            home_team=cls.team1,
            away_team=cls.team2,
            match_date=timezone.now() + datetime.timedelta(days=1)
        )

    def test_match_creation(self):
        """Test membuat instance Match."""
        self.assertIsInstance(self.match, Match)
        self.assertEqual(self.match.tournament, self.tournament)
        self.assertEqual(self.match.home_team, self.team1)
        self.assertEqual(self.match.away_team, self.team2)
        self.assertIsNone(self.match.home_score) # Skor awal harus None
        self.assertIsNone(self.match.away_score)

    def test_match_str_representation(self):
        """Test representasi string model Match."""
        expected_str = f"Team Alpha vs Team Beta (Match Test Tournament)"
        self.assertEqual(str(self.match), expected_str)

class TournamentFormTest(TestCase):
    """Pengujian untuk TournamentForm."""

    def test_valid_form(self):
        """Test form valid dengan data benar."""
        form_data = {
            'name': 'Valid Tournament',
            'description': 'Valid description.',
            'banner': 'http://example.com/banner.jpg',
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + datetime.timedelta(days=1)
        }
        form = TournamentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_form_missing_required_fields(self):
        """Test form tidak valid jika field wajib kosong."""
        form_data = {'description': 'Only description'}
        form = TournamentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('start_date', form.errors)
        self.assertIn('end_date', form.errors)

    def test_invalid_form_end_date_before_start_date(self):
        """Test form tidak valid jika tanggal selesai sebelum tanggal mulai."""
        form_data = {
            'name': 'Invalid Date Tournament',
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() - datetime.timedelta(days=1)
        }
        form = TournamentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors) # Error non-field
        self.assertIn('Tanggal selesai tidak boleh sebelum tanggal mulai.', form.errors['__all__'][0])

    def test_form_banner_optional(self):
        """Test form valid meskipun banner URL kosong."""
        form_data = {
            'name': 'No Banner Tournament',
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + datetime.timedelta(days=1)
        }
        form = TournamentForm(data=form_data)
        self.assertTrue(form.is_valid())

class TournamentViewsTest(TestCase):
    """Pengujian untuk semua view di aplikasi tournaments."""

    @classmethod
    def setUpTestData(cls):
        # Buat user dengan role berbeda
        cls.admin_user = create_user_with_profile("admin_user", "password123", "ADMIN")
        cls.organizer_user = create_user_with_profile("org_user", "password123", "PENYELENGGARA")
        cls.organizer_user2 = create_user_with_profile("org_user2", "password123", "PENYELENGGARA")
        cls.player_user = create_user_with_profile("player_user", "password123", "PEMAIN")

        # Buat beberapa turnamen untuk testing
        cls.t1 = Tournament.objects.create(
            name="Tournament 1 Ongoing", organizer=cls.organizer_user,
            start_date=timezone.now().date() - datetime.timedelta(days=1),
            end_date=timezone.now().date() + datetime.timedelta(days=5)
        )
        cls.t2 = Tournament.objects.create(
            name="Tournament 2 Upcoming", organizer=cls.organizer_user2,
            start_date=timezone.now().date() + datetime.timedelta(days=2),
            end_date=timezone.now().date() + datetime.timedelta(days=10)
        )
        cls.t3 = Tournament.objects.create(
            name="Tournament 3 Past", organizer=cls.organizer_user,
            start_date=timezone.now().date() - datetime.timedelta(days=10),
            end_date=timezone.now().date() - datetime.timedelta(days=2)
        )

        # Buat match untuk detail view
        cls.team_a = Team.objects.create(name="Team A Test")
        cls.team_b = Team.objects.create(name="Team B Test")
        cls.match1 = Match.objects.create(
            tournament=cls.t1, home_team=cls.team_a, away_team=cls.team_b,
            match_date=timezone.now() + datetime.timedelta(hours=2)
        )

    def setUp(self):
        # Setup client di setiap test method
        self.client = Client()
        self.client_admin = Client()
        self.client_organizer = Client()
        self.client_organizer2 = Client()
        self.client_player = Client()

        self.client_admin.login(username="admin_user", password="password123")
        self.client_organizer.login(username="org_user", password="password123")
        self.client_organizer2.login(username="org_user2", password="password123")
        self.client_player.login(username="player_user", password="password123")


    # --- Test tournament_home (HTML Page) ---
    def test_tournament_home_view_loads(self):
        """Test halaman daftar turnamen (HTML) bisa diakses."""
        response = self.client.get(reverse('tournaments:tournament_home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/tournament_list.html')
        # Cek context berisi form create (karena view ini juga render modal)
        self.assertIsInstance(response.context['create_form'], TournamentForm)


    # --- Test get_tournaments_json (AJAX Endpoint) ---
    def test_get_tournaments_json_format_and_content(self):
        """Test endpoint JSON daftar turnamen mengembalikan format yang benar."""
        response = self.client.get(reverse('tournaments:get_tournaments_json'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3) # Ada 3 turnamen
        # Cek data turnamen pertama (diurut berdasarkan start_date desc)
        self.assertEqual(data[0]['name'], "Tournament 2 Upcoming")
        self.assertEqual(data[0]['organizer'], "org_user2")
        self.assertIn('detail_page_url', data[0])

    def test_get_tournaments_json_search_filter(self):
        """Test filter pencarian di endpoint JSON."""
        response = self.client.get(reverse('tournaments:get_tournaments_json') + '?search=Ongoing')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Tournament 1 Ongoing")

    def test_get_tournaments_json_status_filter_ongoing(self):
        """Test filter status 'ongoing' di endpoint JSON."""
        response = self.client.get(reverse('tournaments:get_tournaments_json') + '?status=ongoing')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Tournament 1 Ongoing")

    def test_get_tournaments_json_status_filter_upcoming(self):
        """Test filter status 'upcoming' di endpoint JSON."""
        response = self.client.get(reverse('tournaments:get_tournaments_json') + '?status=upcoming')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Tournament 2 Upcoming")

    def test_get_tournaments_json_status_filter_past(self):
        """Test filter status 'past' di endpoint JSON."""
        response = self.client.get(reverse('tournaments:get_tournaments_json') + '?status=past')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Tournament 3 Past")


    # --- Test create_tournament (AJAX Endpoint) ---
    def test_create_tournament_by_organizer(self):
        """Test organizer bisa membuat turnamen via AJAX POST."""
        post_data = {
            'name': 'New Tournament by Org',
            'description': 'Desc',
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + datetime.timedelta(days=3)
        }
        response = self.client_organizer.post(reverse('tournaments:create_tournament'), post_data)
        self.assertEqual(response.status_code, 201) # Created
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['tournament']['name'], 'New Tournament by Org')
        self.assertTrue(Tournament.objects.filter(name='New Tournament by Org').exists())

    def test_create_tournament_by_admin(self):
        """Test admin bisa membuat turnamen via AJAX POST."""
        post_data = {
            'name': 'New Tournament by Admin',
            'description': 'Desc Admin',
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + datetime.timedelta(days=3)
        }
        response = self.client_admin.post(reverse('tournaments:create_tournament'), post_data)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(Tournament.objects.filter(name='New Tournament by Admin').exists())

    def test_create_tournament_by_player_forbidden(self):
        """Test player tidak bisa membuat turnamen."""
        post_data = {'name': 'Player Tourn', 'start_date': timezone.now().date(), 'end_date': timezone.now().date()}
        response = self.client_player.post(reverse('tournaments:create_tournament'), post_data)
        self.assertEqual(response.status_code, 403) # Forbidden
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Akses ditolak', data['message'])
        self.assertFalse(Tournament.objects.filter(name='Player Tourn').exists())

    def test_create_tournament_anonymous_forbidden(self):
        """Test user anonim tidak bisa membuat turnamen."""
        post_data = {'name': 'Anon Tourn', 'start_date': timezone.now().date(), 'end_date': timezone.now().date()}
        response = self.client.post(reverse('tournaments:create_tournament'), post_data)
        # Akan redirect ke login karena @login_required
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
        self.assertFalse(Tournament.objects.filter(name='Anon Tourn').exists())

    def test_create_tournament_invalid_data(self):
        """Test create gagal jika data form tidak valid (via AJAX)."""
        post_data = { # Missing name, end_date before start_date
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() - datetime.timedelta(days=1)
        }
        response = self.client_organizer.post(reverse('tournaments:create_tournament'), post_data)
        self.assertEqual(response.status_code, 400) # Bad Request
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('name', data['errors'])
        self.assertIn('__all__', data['errors']) # Error end date < start date
        self.assertIn('Tanggal selesai tidak boleh sebelum tanggal mulai.', data['errors']['__all__'][0]['message'])

    # --- Test tournament_detail_page (HTML Shell) ---
    def test_tournament_detail_page_loads(self):
        """Test halaman detail (HTML) bisa diakses."""
        response = self.client.get(reverse('tournaments:tournament_detail_page', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/tournament_detail.html')
        # Cek context berisi ID turnamen dan form edit (kosong)
        self.assertEqual(response.context['tournament_id'], self.t1.pk)
        self.assertIsInstance(response.context['edit_form'], TournamentForm)

    def test_tournament_detail_page_not_found(self):
        """Test halaman detail mengembalikan 404 jika ID tidak valid."""
        response = self.client.get(reverse('tournaments:tournament_detail_page', args=[9999]))
        self.assertEqual(response.status_code, 404)


    # --- Test get_tournament_detail_json (AJAX Endpoint) ---
    def test_get_tournament_detail_json_format_content(self):
        """Test endpoint JSON detail mengembalikan format dan data yang benar."""
        response = self.client.get(reverse('tournaments:get_tournament_detail_json', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['id'], self.t1.pk)
        self.assertEqual(data['name'], "Tournament 1 Ongoing")
        self.assertEqual(data['organizer_username'], self.organizer_user.username)
        self.assertIsInstance(data['matches'], list)
        self.assertEqual(len(data['matches']), 1)
        self.assertEqual(data['matches'][0]['home_team_name'], self.team_a.name)
        self.assertIn('forum_url', data)
        self.assertIn('predictions_url', data)
        self.assertIn('is_organizer_or_admin', data)

    def test_get_tournament_detail_json_organizer_flag(self):
        """Test flag is_organizer_or_admin benar untuk organizer."""
        response = self.client_organizer.get(reverse('tournaments:get_tournament_detail_json', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['is_organizer_or_admin'])

    def test_get_tournament_detail_json_admin_flag(self):
        """Test flag is_organizer_or_admin benar untuk admin."""
        response = self.client_admin.get(reverse('tournaments:get_tournament_detail_json', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['is_organizer_or_admin'])

    def test_get_tournament_detail_json_player_flag(self):
        """Test flag is_organizer_or_admin salah untuk player."""
        response = self.client_player.get(reverse('tournaments:get_tournament_detail_json', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['is_organizer_or_admin'])

    def test_get_tournament_detail_json_anonymous_flag(self):
        """Test flag is_organizer_or_admin salah untuk user anonim."""
        response = self.client.get(reverse('tournaments:get_tournament_detail_json', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['is_organizer_or_admin'])

    def test_get_tournament_detail_json_not_found(self):
        """Test endpoint JSON detail mengembalikan 404 jika ID tidak valid."""
        response = self.client.get(reverse('tournaments:get_tournament_detail_json', args=[9999]))
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Tournament not found')


    # --- Test edit_tournament (AJAX Endpoint) ---
    def test_edit_tournament_by_organizer(self):
        """Test organizer bisa mengedit turnamennya via AJAX POST."""
        post_data = {
            'name': 'Tournament 1 Edited by Org',
            'description': 'Updated Desc',
            'start_date': self.t1.start_date, # Tanggal tidak diubah
            'end_date': self.t1.end_date,
            'banner': 'http://new.com/banner.png'
        }
        response = self.client_organizer.post(reverse('tournaments:edit_tournament', args=[self.t1.pk]), post_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['tournament']['name'], 'Tournament 1 Edited by Org')
        self.assertEqual(data['tournament']['banner_url'], 'http://new.com/banner.png')
        self.t1.refresh_from_db() # Reload data dari DB
        self.assertEqual(self.t1.name, 'Tournament 1 Edited by Org')
        self.assertEqual(self.t1.banner, 'http://new.com/banner.png')

    def test_edit_tournament_by_admin(self):
        """Test admin bisa mengedit turnamen orang lain via AJAX POST."""
        post_data = {
            'name': 'Tournament 1 Edited by Admin',
            'start_date': self.t1.start_date,
            'end_date': self.t1.end_date
        }
        response = self.client_admin.post(reverse('tournaments:edit_tournament', args=[self.t1.pk]), post_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.name, 'Tournament 1 Edited by Admin')

    def test_edit_tournament_by_other_organizer_forbidden(self):
        """Test organizer lain tidak bisa mengedit turnamen orang lain."""
        post_data = {'name': 'Edit Attempt'}
        response = self.client_organizer2.post(reverse('tournaments:edit_tournament', args=[self.t1.pk]), post_data)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Akses ditolak', data['message'])
        self.t1.refresh_from_db()
        self.assertNotEqual(self.t1.name, 'Edit Attempt') # Pastikan nama tidak berubah

    def test_edit_tournament_by_player_forbidden(self):
        """Test player tidak bisa mengedit turnamen."""
        post_data = {'name': 'Player Edit Attempt'}
        response = self.client_player.post(reverse('tournaments:edit_tournament', args=[self.t1.pk]), post_data)
        self.assertEqual(response.status_code, 403)

    def test_edit_tournament_anonymous_forbidden(self):
        """Test user anonim tidak bisa mengedit turnamen."""
        post_data = {'name': 'Anon Edit Attempt'}
        response = self.client.post(reverse('tournaments:edit_tournament', args=[self.t1.pk]), post_data)
        self.assertEqual(response.status_code, 302) # Redirect ke login
        self.assertIn('/login/', response.url)

    def test_edit_tournament_invalid_data(self):
        """Test edit gagal jika data form tidak valid (via AJAX)."""
        post_data = {
            'name': 'Invalid Edit',
            'start_date': self.t1.start_date,
            'end_date': self.t1.start_date - datetime.timedelta(days=1) # End date invalid
        }
        response = self.client_organizer.post(reverse('tournaments:edit_tournament', args=[self.t1.pk]), post_data)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('__all__', data['errors'])
        self.assertIn('Tanggal selesai tidak boleh sebelum tanggal mulai.', data['errors']['__all__'][0]['message'])
        self.t1.refresh_from_db()
        self.assertNotEqual(self.t1.name, 'Invalid Edit') # Pastikan nama tidak berubah


    # --- Test delete_tournament (AJAX Endpoint) ---
    def test_delete_tournament_by_organizer(self):
        """Test organizer bisa menghapus turnamennya via AJAX DELETE."""
        # Buat turnamen baru khusus untuk tes delete ini
        tourn_to_delete = Tournament.objects.create(name="Delete Me Org", organizer=self.organizer_user, start_date=timezone.now().date(), end_date=timezone.now().date())
        tourn_id = tourn_to_delete.pk
        response = self.client_organizer.delete(reverse('tournaments:delete_tournament', args=[tourn_id]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertIn('berhasil dihapus', data['message'])
        self.assertEqual(data['redirect_url'], reverse('tournaments:tournament_home'))
        self.assertFalse(Tournament.objects.filter(pk=tourn_id).exists()) # Verifikasi sudah terhapus

    def test_delete_tournament_by_admin(self):
        """Test admin bisa menghapus turnamen orang lain via AJAX DELETE."""
        tourn_to_delete = Tournament.objects.create(name="Delete Me Admin", organizer=self.organizer_user, start_date=timezone.now().date(), end_date=timezone.now().date())
        tourn_id = tourn_to_delete.pk
        response = self.client_admin.delete(reverse('tournaments:delete_tournament', args=[tourn_id]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertFalse(Tournament.objects.filter(pk=tourn_id).exists())

    def test_delete_tournament_by_other_organizer_forbidden(self):
        """Test organizer lain tidak bisa menghapus turnamen orang lain."""
        response = self.client_organizer2.delete(reverse('tournaments:delete_tournament', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Akses ditolak', data['message'])
        self.assertTrue(Tournament.objects.filter(pk=self.t1.pk).exists()) # Pastikan tidak terhapus

    def test_delete_tournament_by_player_forbidden(self):
        """Test player tidak bisa menghapus turnamen."""
        response = self.client_player.delete(reverse('tournaments:delete_tournament', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 403)

    def test_delete_tournament_anonymous_forbidden(self):
        """Test user anonim tidak bisa menghapus turnamen."""
        response = self.client.delete(reverse('tournaments:delete_tournament', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 302) # Redirect ke login

    def test_delete_tournament_not_found(self):
        """Test delete mengembalikan 404 jika ID tidak valid."""
        response = self.client_admin.delete(reverse('tournaments:delete_tournament', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_delete_tournament_uses_delete_method_only(self):
        """Test endpoint delete menolak metode selain DELETE."""
        # Coba GET
        response_get = self.client_organizer.get(reverse('tournaments:delete_tournament', args=[self.t1.pk]))
        self.assertEqual(response_get.status_code, 405) # Method Not Allowed
        # Coba POST
        response_post = self.client_organizer.post(reverse('tournaments:delete_tournament', args=[self.t1.pk]))
        self.assertEqual(response_post.status_code, 405)
        # Coba PUT
        response_put = self.client_organizer.put(reverse('tournaments:delete_tournament', args=[self.t1.pk]))
        self.assertEqual(response_put.status_code, 405)
        # Pastikan tidak terhapus
        self.assertTrue(Tournament.objects.filter(pk=self.t1.pk).exists())
