from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import datetime, timedelta

from tournaments.models import Tournament, Match, Prediction
from teams.models import Team

class PredictionTestCase(TestCase):
    def setUp(self):
        # Buat user dan login
        self.client = Client()
        self.user = User.objects.create_user(username='asri', password='password123')
        self.client.login(username='asri', password='password123')

        # Buat tournament
        self.tournament = Tournament.objects.create(
            name="Turnamen Tes",
            description="Turnamen Unit Test",
            organizer=self.user,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=7),
        )

        # Buat 2 tim
        self.team_a = Team.objects.create(name="Team A")
        self.team_b = Team.objects.create(name="Team B")

        # Tambahkan ke turnamen
        self.tournament.participants.add(self.team_a, self.team_b)

        # Buat pertandingan
        self.match = Match.objects.create(
            tournament=self.tournament,
            home_team=self.team_a,
            away_team=self.team_b,
            match_date=datetime.now() + timedelta(days=1)
        )

    def test_submit_prediction(self):
        """User dapat membuat prediksi via AJAX dan tersimpan di database"""
        response = self.client.post(reverse('tournaments:submit_prediction'), {
            'match_id': self.match.id,
            'team_id': self.team_a.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Prediction.objects.filter(user=self.user, match=self.match).exists())

    def test_unique_prediction_per_match(self):
        """User hanya bisa memiliki satu prediksi per pertandingan"""
        Prediction.objects.create(user=self.user, match=self.match, predicted_winner=self.team_a)
        # Coba buat prediksi kedua (harus update, bukan buat baru)
        response = self.client.post(reverse('tournaments:submit_prediction'), {
            'match_id': self.match.id,
            'team_id': self.team_b.id
        })
        self.assertEqual(Prediction.objects.count(), 1)
        pred = Prediction.objects.get(user=self.user, match=self.match)
        self.assertEqual(pred.predicted_winner, self.team_b)

    def test_evaluate_prediction_correct(self):
        """Prediksi yang benar mendapat 10 poin"""
        # User prediksi Team A menang
        Prediction.objects.create(user=self.user, match=self.match, predicted_winner=self.team_a)

        # Set hasil pertandingan
        self.match.home_score = 2
        self.match.away_score = 1
        self.match.save()

        # Jalankan evaluasi
        response = self.client.get(reverse('tournaments:evaluate_predictions', args=[self.match.id]))
        self.assertEqual(response.status_code, 200)

        prediction = Prediction.objects.get(user=self.user, match=self.match)
        self.assertEqual(prediction.points_awarded, 10)

    def test_evaluate_prediction_wrong(self):
        """Prediksi yang salah mendapat 0 poin"""
        # User prediksi Team B menang
        Prediction.objects.create(user=self.user, match=self.match, predicted_winner=self.team_b)

        # Hasil: Team A menang
        self.match.home_score = 3
        self.match.away_score = 0
        self.match.save()

        response = self.client.get(reverse('tournaments:evaluate_predictions', args=[self.match.id]))
        self.assertEqual(response.status_code, 200)

        prediction = Prediction.objects.get(user=self.user, match=self.match)
        self.assertEqual(prediction.points_awarded, 0)

    def test_leaderboard_view(self):
        """Leaderboard menampilkan user dengan total poin"""
        # Buat prediksi benar
        pred = Prediction.objects.create(user=self.user, match=self.match, predicted_winner=self.team_a)
        self.match.home_score = 1
        self.match.away_score = 0
        self.match.save()
        pred.points_awarded = 10
        pred.save()

        response = self.client.get(reverse('tournaments:leaderboard_view', args=[self.tournament.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)
