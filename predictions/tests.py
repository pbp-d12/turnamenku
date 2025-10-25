from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from predictions.models import Prediction
from tournaments.models import Match, Tournament
from teams.models import Team
from django.utils.dateparse import parse_datetime

class PredictionViewTests(TestCase):
    def setUp(self):
        # Client
        self.client = Client()

        # Users
        self.user = User.objects.create_user(username='user', password='pass')
        self.admin = User.objects.create_user(username='admin', password='pass')

        # Buat role di profile
        self.user.profile.role = 'USER'
        self.user.profile.save()
        self.admin.profile.role = 'ADMIN'
        self.admin.profile.save()

        # Teams
        self.teamA = Team.objects.create(name='Team A')
        self.teamB = Team.objects.create(name='Team B')
        self.teamC = Team.objects.create(name='Team C') 

        # Tournament
        self.tournament = Tournament.objects.create(
            name='Test Cup',
            organizer=self.admin,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=5)
        )
        self.tournament.participants.add(self.teamA, self.teamB)

        # Match
        self.match = Match.objects.create(
            tournament=self.tournament,
            home_team=self.teamA,
            away_team=self.teamB,
            match_date=timezone.now()
        )

    def test_submit_prediction_success(self):
        self.client.login(username='user', password='pass')
        response = self.client.post(
            reverse('predictions:submit_prediction'),
            {'match_id': self.match.id, 'team_id': self.teamA.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Prediction.objects.filter(user=self.user, match=self.match).exists())

    def test_submit_prediction_invalid_team(self):
        self.client.login(username='user', password='pass')
        response = self.client.post(
            reverse('predictions:submit_prediction'),
            {'match_id': self.match.id, 'team_id': self.teamC.id}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Tim tidak valid', response.json()['message'])

    def test_delete_prediction_permission(self):
        self.client.login(username='user', password='pass')
        Prediction.objects.create(user=self.user, match=self.match, predicted_winner=self.teamA)
        response = self.client.post(
            reverse('predictions:delete_prediction'),
            {'match_id': self.match.id}
        )
        self.assertEqual(response.status_code, 403)

        # login admin
        self.client.login(username='admin', password='pass')
        response = self.client.post(
            reverse('predictions:delete_prediction'),
            {'match_id': self.match.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Prediction.objects.filter(match=self.match).exists())

    def test_add_match_permission(self):
        self.client.login(username='user', password='pass')
        response = self.client.post(
            reverse('predictions:add_match'),
            {
                'tournament': self.tournament.id,
                'home_team': self.teamA.id,
                'away_team': self.teamB.id,
                'match_date': (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
            }
        )
        self.assertEqual(response.status_code, 403)

        self.client.login(username='admin', password='pass')
        response = self.client.post(
            reverse('predictions:add_match'),
            {
                'tournament': self.tournament.id,
                'home_team': self.teamA.id,
                'away_team': self.teamB.id,
                'match_date': (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Match.objects.filter(home_team=self.teamA, away_team=self.teamB).exists())

    def test_edit_match_score(self):
        self.client.login(username='admin', password='pass')
        response = self.client.post(
            reverse('predictions:edit_match_score'),
            {'match_id': self.match.id, 'home_score': 2, 'away_score': 1}
        )
        self.assertEqual(response.status_code, 200)
        self.match.refresh_from_db()
        self.assertEqual(self.match.home_score, 2)
        self.assertEqual(self.match.away_score, 1)

    def test_evaluate_predictions(self):
        self.client.login(username='user', password='pass')
        
        Prediction.objects.all().delete()
        
        pred = Prediction.objects.create(user=self.user, match=self.match, predicted_winner=self.teamA)
        self.match.home_score = 2
        self.match.away_score = 1
        self.match.save()

        response = self.client.get(reverse('predictions:evaluate_predictions', args=[self.match.id]))
        self.assertEqual(response.status_code, 200)
        pred.refresh_from_db()
        self.assertEqual(pred.points_awarded, 10)


    def test_get_match_scores(self):
        self.match.home_score = 3
        self.match.away_score = 2
        self.match.save()
        response = self.client.get(reverse('predictions:get_match_scores', args=[self.match.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'home_score': 3, 'away_score': 2})


    def test_add_match_invalid_team_or_same_team(self):
        self.client.login(username='admin', password='pass')

        # tim tidak di turnamen
        response = self.client.post(
            reverse('predictions:add_match'),
            {
                'tournament': self.tournament.id,
                'home_team': self.teamA.id,
                'away_team': self.teamC.id,
                'match_date': (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
            }
        )
        self.assertEqual(response.status_code, 400)

        # tim sama
        response = self.client.post(
            reverse('predictions:add_match'),
            {
                'tournament': self.tournament.id,
                'home_team': self.teamA.id,
                'away_team': self.teamA.id,
                'match_date': (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
            }
        )
        self.assertEqual(response.status_code, 400)

        # metode GET (bukan POST)
        response = self.client.get(reverse('predictions:add_match'))
        self.assertEqual(response.status_code, 400)

    def test_delete_prediction_not_found_and_invalid_method(self):
        self.client.login(username='admin', password='pass')
        # tidak ada prediction
        response = self.client.post(
            reverse('predictions:delete_prediction'),
            {'match_id': 9999}
        )
        self.assertEqual(response.json()['success'], False)

        # bukan POST
        response = self.client.get(reverse('predictions:delete_prediction'))
        self.assertEqual(response.status_code, 400)

    def test_submit_prediction_invalid_method(self):
        self.client.login(username='user', password='pass')
        response = self.client.get(reverse('predictions:submit_prediction'))
        self.assertEqual(response.status_code, 400)

    def test_evaluate_predictions_draw_and_incomplete(self):
        self.client.login(username='admin', password='pass')
        # belum selesai
        response = self.client.get(reverse('predictions:evaluate_predictions', args=[self.match.id]))
        self.assertEqual(response.status_code, 400)

        # hasil draw
        self.match.home_score = 1
        self.match.away_score = 1
        self.match.save()
        Prediction.objects.create(user=self.user, match=self.match, predicted_winner=self.teamA)
        response = self.client.get(reverse('predictions:evaluate_predictions', args=[self.match.id]))
        self.assertEqual(response.status_code, 200)
        pred = Prediction.objects.get(user=self.user, match=self.match)
        self.assertEqual(pred.points_awarded, 0)

    def test_get_ongoing_and_finished_matches_views(self):
        # ongoing
        response = self.client.get(reverse('predictions:get_ongoing_matches'))
        self.assertEqual(response.status_code, 200)

        # finished
        self.match.home_score = 2
        self.match.away_score = 1
        self.match.save()
        response = self.client.get(reverse('predictions:get_finished_matches'))
        self.assertEqual(response.status_code, 200)

    def test_predictions_index_and_leaderboard(self):
        # predictions_index
        response = self.client.get(reverse('predictions:predictions_index'))
        self.assertEqual(response.status_code, 200)

        # leaderboard default & ascending
        response = self.client.get(reverse('predictions:leaderboard'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('predictions:leaderboard') + '?sort=asc')
        self.assertEqual(response.status_code, 200)
