from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import models
from django.contrib.auth.decorators import login_required
from predictions.models import Prediction
from tournaments.models import Match
from teams.models import Team


def predictions_index(request):
    """
    Menampilkan daftar pertandingan yang belum selesai.
    Pengguna dapat memberikan prediksi pemenang (klik tim).
    """
    matches = Match.objects.filter(home_score__isnull=True, away_score__isnull=True)
    return render(request, 'predictions/predictions_index.html', {'matches': matches})


@login_required
def submit_prediction(request):
    """
    Menerima prediksi pengguna via AJAX dan menyimpannya ke database.
    """
    if request.method == 'POST':
        match_id = request.POST.get('match_id')
        team_id = request.POST.get('team_id')

        match = get_object_or_404(Match, id=match_id)
        team = get_object_or_404(Team, id=team_id)

        if team not in [match.home_team, match.away_team]:
            return JsonResponse({'success': False, 'message': 'Tim tidak valid untuk pertandingan ini.'}, status=400)

        prediction, created = Prediction.objects.update_or_create(
            user=request.user,
            match=match,
            defaults={'predicted_winner': team}
        )

        return JsonResponse({
            'success': True,
            'message': f'Prediksi {team.name} disimpan!',
            'team': team.name,
        })

    return JsonResponse({'success': False, 'message': 'Permintaan tidak valid.'}, status=400)


def leaderboard_view(request):
    """
    Menampilkan leaderboard berdasarkan total poin.
    """
    leaderboard = (
        Prediction.objects.values('user__username')
        .annotate(total_points=models.Sum('points_awarded'))
        .order_by('-total_points')
    )
    return render(request, 'predictions/leaderboard.html', {'leaderboard': leaderboard})


@login_required
def evaluate_predictions(request, match_id):
    """
    Menghitung poin berdasarkan hasil pertandingan.
    """
    match = get_object_or_404(Match, id=match_id)

    if match.home_score is None or match.away_score is None:
        return JsonResponse({'success': False, 'message': 'Pertandingan belum selesai.'}, status=400)

    # Tentukan pemenang
    if match.home_score > match.away_score:
        correct_team = match.home_team
    elif match.away_score > match.home_score:
        correct_team = match.away_team
    else:
        correct_team = None

    predictions = Prediction.objects.filter(match=match)

    for p in predictions:
        p.points_awarded = 10 if correct_team and p.predicted_winner == correct_team else 0
        p.save()

    return JsonResponse({'success': True, 'message': 'Prediksi telah dievaluasi!'})
