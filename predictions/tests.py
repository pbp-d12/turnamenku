from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from predictions.models import Prediction
from tournaments.models import Match, Tournament
from teams.models import Team

class PredictionViewTests(TestCase):
    def setUp(self):
        # Setup data dasar
        self.client = Client()
        self.user = User.objects.create_user(username='asri', password='test123')
        self.client.login(username='asri', password='test123')

        # Buat Tournament dummy
        self.tournament = Tournament.objects.create(
            name="Turnamen Uji",
            description="Turnamen untuk testing",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            organizer=self.user
        )

        # Buat tim dan pertandingan
        self.teamA = Team.objects.create(name='Team A')
        self.teamB = Team.objects.create(name='Team B')
        self.match = Match.objects.create(
            tournament=self.tournament,
            home_team=self.teamA,
            away_team=self.teamB,
            match_date=timezone.now().date()
        )

    def test_submit_prediction_success(self):
        """Cek apakah prediksi bisa disimpan dengan benar via AJAX"""
        response = self.client.post(
            reverse('predictions:submit_prediction'),
            {'match_id': self.match.id, 'team_id': self.teamA.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'success': True, 'message': 'Prediksi Team A disimpan!', 'team': 'Team A'}
        )

        prediction = Prediction.objects.get(user=self.user, match=self.match)
        self.assertEqual(prediction.predicted_winner, self.teamA)

    def test_submit_prediction_invalid_team(self):
        """Cek jika user memilih tim yang tidak ikut pertandingan"""
        teamC = Team.objects.create(name='Team C')
        response = self.client.post(
            reverse('predictions:submit_prediction'),
            {'match_id': self.match.id, 'team_id': teamC.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Tim tidak valid', response.json()['message'])

    def test_submit_prediction_not_logged_in(self):
        """Cek kalau user belum login"""
        self.client.logout()
        response = self.client.post(
            reverse('predictions:submit_prediction'),
            {'match_id': self.match.id, 'team_id': self.teamA.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/?next=/predictions/submit/', response.url)


class LeaderboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='asri', password='test123')
        self.user2 = User.objects.create_user(username='budi', password='test123')

        # Buat Tournament dummy
        self.tournament = Tournament.objects.create(
            name="Turnamen Uji",
            description="Turnamen untuk leaderboard",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            organizer=self.user1
        )

        self.teamA = Team.objects.create(name='Team A')
        self.teamB = Team.objects.create(name='Team B')
        self.match = Match.objects.create(
            tournament=self.tournament,
            home_team=self.teamA,
            away_team=self.teamB,
            match_date=timezone.now().date()
        )

        Prediction.objects.create(user=self.user1, match=self.match, predicted_winner=self.teamA, points_awarded=10)
        Prediction.objects.create(user=self.user2, match=self.match, predicted_winner=self.teamB, points_awarded=5)

    def test_leaderboard_view_status_code(self):
        """Halaman leaderboard dapat diakses"""
        response = self.client.get(reverse('predictions:leaderboard'))
        self.assertEqual(response.status_code, 200)

    def test_leaderboard_ordering(self):
        """Leaderboard diurutkan dari poin tertinggi"""
        response = self.client.get(reverse('predictions:leaderboard'))
        leaderboard = list(response.context['leaderboard'])
        self.assertEqual(leaderboard[0]['user__username'], 'asri')
        self.assertEqual(leaderboard[0]['total_points'], 10)
        self.assertEqual(leaderboard[1]['user__username'], 'budi')
        self.assertEqual(leaderboard[1]['total_points'], 5)
