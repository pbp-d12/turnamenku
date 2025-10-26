import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse, resolve
from django.utils import timezone

from main.models import Profile  
from teams.models import Team
from .forms import TournamentForm
from .models import Match, Tournament
from .views import (
    create_tournament, delete_tournament, deregister_team_view,
    edit_tournament, get_tournament_detail_json, get_tournaments_json,
    get_user_captain_status, register_team_view, remove_team_view,
    search_teams_json, tournament_detail_page, tournament_home
)



def create_user_with_profile(username, password, role='PEMAIN', is_superuser=False):
    """Creates a user and their associated profile."""
    if is_superuser:
        user = User.objects.create_superuser(username=username, password=password, email=f"{username}@test.com")
      
        profile = Profile.objects.get(user=user)
        if profile.role != 'ADMIN': 
             profile.role = 'ADMIN'
             profile.save()
    else:
        user = User.objects.create_user(username=username, password=password, email=f"{username}@test.com")
        profile, created = Profile.objects.get_or_create(user=user, defaults={'role': role})
        if not created and profile.role != role:
            profile.role = role
            profile.save()
    return user, profile

class BaseTournamentTestCase(TestCase):
    """Base test case with setup for common data."""

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.organizer_user, cls.organizer_profile = create_user_with_profile(
            "organizer", "password", role='PENYELENGGARA'
        )
        cls.admin_user, cls.admin_profile = create_user_with_profile(
            "admin", "password", is_superuser=True
        )
        cls.player_user, cls.player_profile = create_user_with_profile(
            "player", "password", role='PEMAIN'
        )
        cls.captain_user, cls.captain_profile = create_user_with_profile(
            "captain", "password", role='PEMAIN'
        )
        cls.other_captain_user, cls.other_captain_profile = create_user_with_profile(
            "captain2", "password", role='PEMAIN'
        )


        cls.team1 = Team.objects.create(name="Team Alpha", captain=cls.captain_user)
        cls.team1.members.add(cls.captain_user, cls.player_user) 

        cls.team2 = Team.objects.create(name="Team Beta", captain=cls.other_captain_user)

        cls.team3 = Team.objects.create(name="Team Gamma") 

        cls.now = timezone.now()
        cls.today = cls.now.date()
        cls.past_date = cls.today - timedelta(days=10)
        cls.future_date = cls.today + timedelta(days=10)
        cls.future_date_plus_20 = cls.today + timedelta(days=20)

        cls.ongoing_tournament = Tournament.objects.create(
            name="Ongoing Championship",
            organizer=cls.organizer_user,
            start_date=cls.today - timedelta(days=5),
            end_date=cls.future_date,
            registration_open=False 
        )
        cls.ongoing_tournament.participants.add(cls.team1, cls.team2)

        cls.upcoming_tournament = Tournament.objects.create(
            name="Upcoming League",
            organizer=cls.organizer_user,
            start_date=cls.future_date,
            end_date=cls.future_date_plus_20,
            registration_open=True
        )

        cls.past_tournament = Tournament.objects.create(
            name="Past Cup",
            organizer=cls.admin_user,
            start_date=cls.past_date - timedelta(days=5),
            end_date=cls.past_date,
            registration_open=False,
            winner=cls.team1 
        )
        cls.past_tournament.participants.add(cls.team1)

        cls.match1_ongoing = Match.objects.create(
            tournament=cls.ongoing_tournament,
            home_team=cls.team1,
            away_team=cls.team2,
            match_date=cls.now + timedelta(hours=2) 
        )
        cls.match2_ongoing_finished = Match.objects.create(
            tournament=cls.ongoing_tournament,
            home_team=cls.team2,
            away_team=cls.team1,
            match_date=cls.now - timedelta(days=1),
            home_score=2,
            away_score=1
        )
        cls.match3_past = Match.objects.create(
            tournament=cls.past_tournament,
            home_team=cls.team1,
            away_team=cls.team3, 
            match_date=cls.now - timedelta(days=12),
            home_score=3,
            away_score=0
        )

        cls.client = Client()

class TournamentModelTests(BaseTournamentTestCase):

    def test_tournament_creation(self):
        """Test basic tournament object creation."""
        self.assertEqual(self.ongoing_tournament.name, "Ongoing Championship")
        self.assertEqual(self.ongoing_tournament.organizer, self.organizer_user)
        self.assertTrue(self.ongoing_tournament.participants.count() > 0)
        self.assertFalse(self.ongoing_tournament.registration_open)
        self.assertIsNone(self.ongoing_tournament.winner)

    def test_tournament_str(self):
        """Test the string representation of the Tournament model."""
        self.assertEqual(str(self.upcoming_tournament), "Upcoming League")

    def test_tournament_defaults(self):
        """Test default values."""
        new_tournament = Tournament.objects.create(
            name="Default Test",
            organizer=self.organizer_user,
            start_date=self.today,
            end_date=self.future_date
        )
        self.assertTrue(new_tournament.registration_open) 
        self.assertIsNone(new_tournament.winner)


class MatchModelTests(BaseTournamentTestCase):

    def test_match_creation(self):
        """Test basic match object creation."""
        self.assertEqual(self.match1_ongoing.tournament, self.ongoing_tournament)
        self.assertEqual(self.match1_ongoing.home_team, self.team1)
        self.assertEqual(self.match1_ongoing.away_team, self.team2)
        self.assertIsNone(self.match1_ongoing.home_score) 
        self.assertIsNone(self.match1_ongoing.away_score)

    def test_match_str(self):
        """Test the string representation of the Match model."""
        expected_str = f"{self.team1.name} vs {self.team2.name} ({self.ongoing_tournament.name})"
        self.assertEqual(str(self.match1_ongoing), expected_str)

    def test_match_scores_nullable(self):
        """Test that scores can be null."""
        self.assertIsNone(self.match1_ongoing.home_score)
        self.match1_ongoing.home_score = 1
        self.match1_ongoing.save()
        self.assertEqual(self.match1_ongoing.home_score, 1)
        self.assertIsNone(self.match1_ongoing.away_score) 


class TournamentFormTests(BaseTournamentTestCase):

    def test_valid_tournament_form(self):
        """Test the tournament form with valid data."""
        form_data = {
            'name': 'Valid Tournament',
            'description': 'A test description.',
            'banner': 'http://example.com/banner.png',
            'start_date': self.today,
            'end_date': self.future_date,
            'participants': [self.team1.pk, self.team2.pk],
            'registration_open': True,
        }
        form = TournamentForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors.as_json()}")

    def test_invalid_tournament_form_dates(self):
        """Test the tournament form with end_date before start_date."""
        form_data = {
            'name': 'Invalid Date Tournament',
            'start_date': self.future_date,
            'end_date': self.today, 
            'registration_open': True,
        }
        form = TournamentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors) 
        self.assertIn("Tanggal selesai tidak boleh sebelum tanggal mulai.", form.errors['__all__'][0])

    def test_invalid_tournament_form_missing_required(self):
        """Test the tournament form with missing required fields."""
        form_data = {
            'description': 'Missing name and dates',
        }
        form = TournamentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('start_date', form.errors)
        self.assertIn('end_date', form.errors)

    def test_tournament_form_participants_optional(self):
        """Test that participants field is not required."""
        form_data = {
            'name': 'No Participants Tourney',
            'start_date': self.today,
            'end_date': self.future_date,
        }
        form = TournamentForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors.as_json()}")

    def test_tournament_form_registration_open_default(self):
        """Test that registration_open defaults to True if not provided."""
        form_data = {
            'name': 'Reg Open Default',
            'start_date': self.today,
            'end_date': self.future_date,
        }
        form = TournamentForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.fields['registration_open'].initial)


class TournamentURLTests(BaseTournamentTestCase):

    def test_urls_resolve_correct_views(self):
        """Test that URL names resolve to the correct view functions/classes."""
        self.assertEqual(resolve(reverse('tournaments:tournament_home')).func, tournament_home)
        self.assertEqual(resolve(reverse('tournaments:get_tournaments_json')).func, get_tournaments_json)
        self.assertEqual(resolve(reverse('tournaments:tournament_detail_page', args=[1])).func, tournament_detail_page)
        self.assertEqual(resolve(reverse('tournaments:get_tournament_detail_json', args=[1])).func, get_tournament_detail_json)
        self.assertEqual(resolve(reverse('tournaments:create_tournament')).func, create_tournament)
        self.assertEqual(resolve(reverse('tournaments:edit_tournament', args=[1])).func, edit_tournament)
        self.assertEqual(resolve(reverse('tournaments:delete_tournament', args=[1])).func, delete_tournament)
        self.assertEqual(resolve(reverse('tournaments:register_team', args=[1])).func, register_team_view)
        self.assertEqual(resolve(reverse('tournaments:get_user_captain_status', args=[1])).func, get_user_captain_status)
        self.assertEqual(resolve(reverse('tournaments:search_teams_json')).func, search_teams_json)
        self.assertEqual(resolve(reverse('tournaments:deregister_team', args=[1])).func, deregister_team_view)
        self.assertEqual(resolve(reverse('tournaments:remove_team', args=[1, 1])).func, remove_team_view)



class TournamentViewTests(BaseTournamentTestCase):

    def test_tournament_home_view_get(self):
        """Test GET request to the tournament home page."""
        response = self.client.get(reverse('tournaments:tournament_home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/tournament_list.html')
        self.assertIn('create_form', response.context)
        self.assertIsInstance(response.context['create_form'], TournamentForm)

    def test_get_tournaments_json_no_filter(self):
        """Test GET request to the JSON endpoint without filters."""
        response = self.client.get(reverse('tournaments:get_tournaments_json'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('tournaments', data)
        self.assertIn('has_next_page', data)
        self.assertIsInstance(data['tournaments'], list)
        self.assertTrue(len(data['tournaments']) <= 9) 

    def test_get_tournaments_json_filter_status(self):
        """Test filtering by status (ongoing, upcoming, past)."""
        response = self.client.get(reverse('tournaments:get_tournaments_json') + '?status=ongoing')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(t['name'] == self.ongoing_tournament.name for t in data['tournaments']))
        self.assertFalse(any(t['name'] == self.upcoming_tournament.name for t in data['tournaments']))

        response = self.client.get(reverse('tournaments:get_tournaments_json') + '?status=upcoming')
        data = response.json()
        self.assertTrue(any(t['name'] == self.upcoming_tournament.name for t in data['tournaments']))
        self.assertFalse(any(t['name'] == self.ongoing_tournament.name for t in data['tournaments']))

        response = self.client.get(reverse('tournaments:get_tournaments_json') + '?status=past')
        data = response.json()
        self.assertTrue(any(t['name'] == self.past_tournament.name for t in data['tournaments']))
        self.assertFalse(any(t['name'] == self.ongoing_tournament.name for t in data['tournaments']))

    def test_get_tournaments_json_search(self):
        """Test searching by name."""
        response = self.client.get(reverse('tournaments:get_tournaments_json') + '?search=Ongoing')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(all('Ongoing' in t['name'] for t in data['tournaments']))
        self.assertEqual(len(data['tournaments']), 1)

    def test_get_tournaments_json_pagination(self):
        """Test pagination."""
        for i in range(15):
             Tournament.objects.create(name=f"Page Test {i}", organizer=self.organizer_user, start_date=self.today, end_date=self.future_date)

        response = self.client.get(reverse('tournaments:get_tournaments_json') + '?page=1')
        data1 = response.json()
        self.assertTrue(data1['has_next_page'])
        self.assertEqual(data1['current_page'], 1)
        self.assertIsNotNone(data1['next_page_number'])

        response = self.client.get(reverse('tournaments:get_tournaments_json') + f"?page={data1['next_page_number']}")
        data2 = response.json()
        self.assertEqual(data2['current_page'], 2)
        names1 = {t['name'] for t in data1['tournaments']}
        names2 = {t['name'] for t in data2['tournaments']}
        self.assertFalse(names1.intersection(names2))

    def test_create_tournament_success_organizer(self):
        """Test successful tournament creation by an organizer."""
        self.client.login(username=self.organizer_user.username, password="password")
        form_data = {
            'name': 'New Organizer Tourney',
            'start_date': self.future_date,
            'end_date': self.future_date_plus_20,
            'participants': [self.team1.pk],
            'registration_open': 'on', 
        }
        response = self.client.post(reverse('tournaments:create_tournament'), form_data)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(Tournament.objects.filter(name='New Organizer Tourney').exists())
        new_tourney = Tournament.objects.get(name='New Organizer Tourney')
        self.assertEqual(new_tourney.organizer, self.organizer_user)
        self.assertTrue(new_tourney.participants.filter(pk=self.team1.pk).exists())
        self.assertTrue(new_tourney.registration_open)

    def test_create_tournament_success_admin(self):
        """Test successful tournament creation by an admin."""
        self.client.login(username=self.admin_user.username, password="password")
        form_data = {
            'name': 'New Admin Tourney',
            'start_date': self.future_date,
            'end_date': self.future_date_plus_20,
        } 
        response = self.client.post(reverse('tournaments:create_tournament'), form_data)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(Tournament.objects.filter(name='New Admin Tourney').exists())
        new_tourney = Tournament.objects.get(name='New Admin Tourney')
        self.assertEqual(new_tourney.organizer, self.admin_user) 
        self.assertTrue(new_tourney.registration_open)

    def test_create_tournament_fail_player(self):
        """Test player cannot create tournament."""
        self.client.login(username=self.player_user.username, password="password")
        form_data = {'name': 'Player Tourney Fail', 'start_date': self.today, 'end_date': self.future_date}
        response = self.client.post(reverse('tournaments:create_tournament'), form_data)
        self.assertEqual(response.status_code, 403) 
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertFalse(Tournament.objects.filter(name='Player Tourney Fail').exists())

    def test_create_tournament_fail_unauthenticated(self):
        """Test unauthenticated user cannot create tournament."""
        form_data = {'name': 'Anon Tourney Fail', 'start_date': self.today, 'end_date': self.future_date}
        response = self.client.post(reverse('tournaments:create_tournament'), form_data)
        self.assertEqual(response.status_code, 302)  
        self.assertFalse(Tournament.objects.filter(name='Anon Tourney Fail').exists())

    def test_create_tournament_fail_invalid_data(self):
        """Test tournament creation fails with invalid form data."""
        self.client.login(username=self.organizer_user.username, password="password")
        form_data = {'name': 'Invalid Data Tourney', 'start_date': self.future_date, 'end_date': self.today} 
        response = self.client.post(reverse('tournaments:create_tournament'), form_data)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('errors', data)
        self.assertIn('__all__', data['errors']) 

    def test_tournament_detail_page_get_exists(self):
        """Test GET request to an existing tournament detail page."""
        response = self.client.get(reverse('tournaments:tournament_detail_page', args=[self.ongoing_tournament.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tournaments/tournament_detail.html')
        self.assertEqual(response.context['tournament_id'], self.ongoing_tournament.pk)
        self.assertIn('edit_form', response.context)

    def test_tournament_detail_page_get_not_exists(self):
        """Test GET request to a non-existent tournament detail page."""
        response = self.client.get(reverse('tournaments:tournament_detail_page', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_get_tournament_detail_json_exists(self):
        """Test GET request to JSON detail endpoint for an existing tournament."""
        response = self.client.get(reverse('tournaments:get_tournament_detail_json', args=[self.ongoing_tournament.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], self.ongoing_tournament.pk)
        self.assertEqual(data['name'], self.ongoing_tournament.name)
        self.assertIn('matches', data)
        self.assertIn('participants', data)
        self.assertIn('leaderboard', data)
        self.assertIn('is_organizer_or_admin', data)
        self.assertIsInstance(data['matches'], list)
        self.assertIsInstance(data['participants'], list)
        self.assertIsInstance(data['leaderboard'], list)
        self.assertTrue(any(m['id'] == self.match1_ongoing.pk for m in data['matches']))
        self.assertTrue(any(p['id'] == self.team1.pk for p in data['participants']))
        if data['leaderboard']:
            self.assertIn('team_name', data['leaderboard'][0])
            self.assertIn('points', data['leaderboard'][0])

    def test_get_tournament_detail_json_not_exists(self):
        """Test GET request to JSON detail endpoint for non-existent tournament."""
        response = self.client.get(reverse('tournaments:get_tournament_detail_json', args=[9999]))
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)

    def test_get_tournament_detail_json_auth_check(self):
        """Test the is_organizer_or_admin flag in JSON detail."""
        response = self.client.get(reverse('tournaments:get_tournament_detail_json', args=[self.ongoing_tournament.pk]))
        self.assertFalse(response.json()['is_organizer_or_admin'])

        self.client.login(username=self.player_user.username, password="password")
        response = self.client.get(reverse('tournaments:get_tournament_detail_json', args=[self.ongoing_tournament.pk]))
        self.assertFalse(response.json()['is_organizer_or_admin'])
        self.client.logout()

        self.client.login(username=self.organizer_user.username, password="password")
        response = self.client.get(reverse('tournaments:get_tournament_detail_json', args=[self.ongoing_tournament.pk]))
        self.assertTrue(response.json()['is_organizer_or_admin'])
        self.client.logout()

        self.client.login(username=self.admin_user.username, password="password")
        response = self.client.get(reverse('tournaments:get_tournament_detail_json', args=[self.ongoing_tournament.pk]))
        self.assertTrue(response.json()['is_organizer_or_admin'])
        self.client.logout()

    def test_edit_tournament_success_organizer(self):
        """Test successful tournament edit by organizer."""
        self.client.login(username=self.organizer_user.username, password="password")
        edit_data = {
            'name': 'Ongoing Championship EDITED',
            'description': 'Updated description.',
            'start_date': self.ongoing_tournament.start_date,
            'end_date': self.future_date_plus_20,  
            'participants': [self.team1.pk], 
            'registration_open': 'on',
        }
        response = self.client.post(reverse('tournaments:edit_tournament', args=[self.ongoing_tournament.pk]), edit_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.ongoing_tournament.refresh_from_db()
        self.assertEqual(self.ongoing_tournament.name, 'Ongoing Championship EDITED')
        self.assertEqual(self.ongoing_tournament.end_date, self.future_date_plus_20)
        self.assertTrue(self.ongoing_tournament.registration_open)
        self.assertEqual(self.ongoing_tournament.participants.count(), 1)
        self.assertTrue(self.ongoing_tournament.participants.filter(pk=self.team1.pk).exists())

    def test_edit_tournament_success_admin(self):
        """Test successful tournament edit by admin."""
        self.client.login(username=self.admin_user.username, password="password")
        edit_data = {'name': 'Admin Edited', 'start_date': self.ongoing_tournament.start_date, 'end_date': self.ongoing_tournament.end_date}
        response = self.client.post(reverse('tournaments:edit_tournament', args=[self.ongoing_tournament.pk]), edit_data)
        self.assertEqual(response.status_code, 200)
        self.ongoing_tournament.refresh_from_db()
        self.assertEqual(self.ongoing_tournament.name, 'Admin Edited')

    def test_edit_tournament_fail_player(self):
        """Test player cannot edit tournament."""
        self.client.login(username=self.player_user.username, password="password")
        edit_data = {'name': 'Player Edit Fail', 'start_date': self.today, 'end_date': self.future_date}
        response = self.client.post(reverse('tournaments:edit_tournament', args=[self.ongoing_tournament.pk]), edit_data)
        self.assertEqual(response.status_code, 403)

    def test_edit_tournament_fail_invalid_data(self):
        """Test tournament edit fails with invalid data."""
        self.client.login(username=self.organizer_user.username, password="password")
        edit_data = {'name': 'Invalid Date Edit', 'start_date': self.future_date, 'end_date': self.today}
        response = self.client.post(reverse('tournaments:edit_tournament', args=[self.ongoing_tournament.pk]), edit_data)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('__all__', data['errors'])

    def test_delete_tournament_success_organizer(self):
        """Test successful tournament deletion by organizer."""
        tourney_to_delete = Tournament.objects.create(name="To Delete", organizer=self.organizer_user, start_date=self.today, end_date=self.future_date)
        pk_to_delete = tourney_to_delete.pk
        self.client.login(username=self.organizer_user.username, password="password")
        response = self.client.delete(reverse('tournaments:delete_tournament', args=[pk_to_delete]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertFalse(Tournament.objects.filter(pk=pk_to_delete).exists())
        self.assertEqual(data['redirect_url'], reverse('tournaments:tournament_home'))

    def test_delete_tournament_success_admin(self):
        """Test successful tournament deletion by admin."""
        tourney_to_delete = Tournament.objects.create(name="Admin Delete", organizer=self.organizer_user, start_date=self.today, end_date=self.future_date)
        pk_to_delete = tourney_to_delete.pk
        self.client.login(username=self.admin_user.username, password="password")
        response = self.client.delete(reverse('tournaments:delete_tournament', args=[pk_to_delete]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tournament.objects.filter(pk=pk_to_delete).exists())

    def test_delete_tournament_fail_player(self):
        """Test player cannot delete tournament."""
        self.client.login(username=self.player_user.username, password="password")
        response = self.client.delete(reverse('tournaments:delete_tournament', args=[self.ongoing_tournament.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Tournament.objects.filter(pk=self.ongoing_tournament.pk).exists())

    def test_delete_tournament_fail_wrong_method(self):
        """Test using GET instead of DELETE fails."""
        self.client.login(username=self.organizer_user.username, password="password")
        response = self.client.get(reverse('tournaments:delete_tournament', args=[self.ongoing_tournament.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Tournament.objects.filter(pk=self.ongoing_tournament.pk).exists())

    def test_register_team_success_captain(self):
        """Test captain successfully registers their team."""
        self.client.login(username=self.captain_user.username, password="password")
        self.upcoming_tournament.participants.remove(self.team1)
        response = self.client.post(reverse('tournaments:register_team', args=[self.upcoming_tournament.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(self.upcoming_tournament.participants.filter(pk=self.team1.pk).exists())

    def test_register_team_fail_not_captain(self):
        """Test non-captain cannot register a team."""
        self.client.login(username=self.player_user.username, password="password")
        response = self.client.post(reverse('tournaments:register_team', args=[self.upcoming_tournament.pk]))
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn("bukan kapten", data['message'])

    def test_register_team_fail_already_registered(self):
        """Test registering an already registered team fails."""
        self.client.login(username=self.captain_user.username, password="password")
        response = self.client.post(reverse('tournaments:register_team', args=[self.ongoing_tournament.pk]))
        self.assertEqual(response.status_code, 400) 
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn("sudah terdaftar", data['message'])

    def test_register_team_fail_registration_closed(self):
        """Test registering for a tournament with closed registration fails."""
        try:
            captained_team = Team.objects.get(captain=self.captain_user)
            if self.ongoing_tournament.participants.filter(pk=captained_team.pk).exists():
                self.ongoing_tournament.participants.remove(captained_team)
        except Team.DoesNotExist:
            pass

        self.client.login(username=self.captain_user.username, password="password")
        response = self.client.post(reverse('tournaments:register_team', args=[self.ongoing_tournament.pk]))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn("sudah ditutup", data['message'])

    def test_get_user_captain_status_captain_can_register(self):
        """Test captain status when they can register for an open tournament."""
        self.client.login(username=self.captain_user.username, password="password")
        self.upcoming_tournament.participants.remove(self.team1) 
        response = self.client.get(reverse('tournaments:get_user_captain_status', args=[self.upcoming_tournament.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['can_register'])
        self.assertTrue(data['is_registration_open'])
        self.assertFalse(data['can_deregister'])
        self.assertEqual(len(data['eligible_teams']), 1)
        self.assertEqual(data['eligible_teams'][0]['id'], self.team1.pk)
        self.assertEqual(len(data['registered_teams']), 0)

    def test_get_user_captain_status_captain_registered(self):
        """Test captain status when their team is already registered."""
        self.client.login(username=self.captain_user.username, password="password")
        self.upcoming_tournament.participants.add(self.team1) 
        response = self.client.get(reverse('tournaments:get_user_captain_status', args=[self.upcoming_tournament.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['can_register'])
        self.assertTrue(data['is_registration_open'])
        self.assertTrue(data['can_deregister'])
        self.assertEqual(len(data['eligible_teams']), 0)
        self.assertEqual(len(data['registered_teams']), 1)
        self.assertEqual(data['registered_teams'][0]['id'], self.team1.pk)

    def test_get_user_captain_status_not_captain(self):
        """Test status for a user who is not a captain."""
        self.client.login(username=self.player_user.username, password="password")
        response = self.client.get(reverse('tournaments:get_user_captain_status', args=[self.upcoming_tournament.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['can_register'])
        self.assertFalse(data['can_deregister'])
        self.assertEqual(len(data['eligible_teams']), 0)
        self.assertEqual(len(data['registered_teams']), 0)

    def test_search_teams_json_found(self):
        """Test searching for teams returns correct JSON."""
        response = self.client.get(reverse('tournaments:search_teams_json') + "?q=Alpha")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Team Alpha')
        self.assertEqual(data[0]['id'], self.team1.pk)

    def test_search_teams_json_not_found(self):
        """Test searching for non-existent team returns empty list."""
        response = self.client.get(reverse('tournaments:search_teams_json') + "?q=NonExistent")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    def test_search_teams_json_short_query(self):
        """Test search with query < 2 chars returns empty list."""
        response = self.client.get(reverse('tournaments:search_teams_json') + "?q=A")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_deregister_team_success_captain(self):
        """Test captain successfully de-registers."""
        self.client.login(username=self.captain_user.username, password="password")
        self.upcoming_tournament.participants.add(self.team1)  
        response = self.client.post(reverse('tournaments:deregister_team', args=[self.upcoming_tournament.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertFalse(self.upcoming_tournament.participants.filter(pk=self.team1.pk).exists())

    def test_deregister_team_fail_not_registered(self):
        """Test de-registering when not registered."""
        self.client.login(username=self.captain_user.username, password="password")
        self.upcoming_tournament.participants.remove(self.team1) 
        response = self.client.post(reverse('tournaments:deregister_team', args=[self.upcoming_tournament.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("tidak terdaftar", response.json()['message'])

    def test_deregister_team_fail_after_match_played(self):
        """Test de-registering fails if a match has been played (scored)."""
        self.client.login(username=self.captain_user.username, password="password")
        self.assertTrue(self.ongoing_tournament.participants.filter(pk=self.team1.pk).exists())
        response = self.client.post(reverse('tournaments:deregister_team', args=[self.ongoing_tournament.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("sudah memainkan pertandingan", response.json()['message'])
        self.assertTrue(self.ongoing_tournament.participants.filter(pk=self.team1.pk).exists()) 

    def test_deregister_team_fail_registration_closed_and_started(self):
        """Test de-register fails if registration closed AND tournament started."""
        self.client.login(username=self.captain_user.username, password="password")
        response = self.client.post(reverse('tournaments:deregister_team', args=[self.ongoing_tournament.pk]))
        started_yesterday = Tournament.objects.create(
            name="Started Yesterday", organizer=self.organizer_user,
            start_date=self.today - timedelta(days=1), end_date=self.future_date,
            registration_open=False
        )
        started_yesterday.participants.add(self.team1)
        response = self.client.post(reverse('tournaments:deregister_team', args=[started_yesterday.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("sudah dimulai", response.json()['message'])


    def test_remove_team_success_organizer(self):
        """Test organizer removes a team."""
        self.client.login(username=self.organizer_user.username, password="password")
        self.ongoing_tournament.participants.add(self.team3)
        self.assertTrue(self.ongoing_tournament.participants.filter(pk=self.team3.pk).exists())
        response = self.client.post(reverse('tournaments:remove_team', args=[self.ongoing_tournament.pk, self.team3.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertFalse(self.ongoing_tournament.participants.filter(pk=self.team3.pk).exists())

    def test_remove_team_success_admin(self):
        """Test admin removes a team."""
        self.client.login(username=self.admin_user.username, password="password")
        self.ongoing_tournament.participants.add(self.team3)
        response = self.client.post(reverse('tournaments:remove_team', args=[self.ongoing_tournament.pk, self.team3.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.ongoing_tournament.participants.filter(pk=self.team3.pk).exists())

    def test_remove_team_fail_player(self):
        """Test player cannot remove a team."""
        self.client.login(username=self.player_user.username, password="password")
        response = self.client.post(reverse('tournaments:remove_team', args=[self.ongoing_tournament.pk, self.team1.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.ongoing_tournament.participants.filter(pk=self.team1.pk).exists())

    def test_remove_team_fail_after_match_played(self):
        """Test removing fails if team has played a scored match."""
        self.client.login(username=self.organizer_user.username, password="password")
        response = self.client.post(reverse('tournaments:remove_team', args=[self.ongoing_tournament.pk, self.team1.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("sudah memainkan pertandingan", response.json()['message'])
        self.assertTrue(self.ongoing_tournament.participants.filter(pk=self.team1.pk).exists())

    def test_remove_team_fail_not_participant(self):
        """Test removing a team not in the tournament."""
        self.client.login(username=self.organizer_user.username, password="password")
        response = self.client.post(reverse('tournaments:remove_team', args=[self.ongoing_tournament.pk, self.team3.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("tidak terdaftar", response.json()['message'])
