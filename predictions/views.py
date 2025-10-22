from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Sum
from teams.models import Team
from tournaments.models import Tournament, Match
from predictions.models import Prediction

# Halaman daftar pertandingan untuk prediksi
@login_required
def prediction_list(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    matches = tournament.matches.all().order_by('match_date')
    user_predictions = Prediction.objects.filter(user=request.user, match__tournament=tournament)
    predicted_match_ids = user_predictions.values_list('match_id', flat=True)

    context = {
        'tournament': tournament,
        'matches': matches,
        'user_predictions': user_predictions,
        'predicted_match_ids': predicted_match_ids,
    }
    return render(request, 'predictions/prediction_list.html', context)


# ================================
# 2️⃣ AJAX handler untuk simpan prediksi
# ================================
@login_required
@require_POST
def submit_prediction(request):
    match_id = request.POST.get('match_id')
    team_id = request.POST.get('team_id')

    match = get_object_or_404(Match, id=match_id)
    team = get_object_or_404(Team, id=team_id)

    prediction, created = Prediction.objects.update_or_create(
        user=request.user,
        match=match,
        defaults={'predicted_winner': team}
    )

    return JsonResponse({
        'success': True,
        'message': f'Prediksi untuk {match} disimpan!',
        'team_name': team.name,
        'created': created
    })


# ================================
# 3️⃣ Evaluasi hasil prediksi (setelah skor dimasukkan)
# ================================
@login_required
def evaluate_predictions(request, match_id):
    """Dipanggil setelah hasil pertandingan dimasukkan oleh penyelenggara."""
    match = get_object_or_404(Match, id=match_id)

    # Tentukan pemenang berdasarkan skor
    if match.home_score is None or match.away_score is None:
        return JsonResponse({'success': False, 'message': 'Skor belum lengkap.'})

    if match.home_score > match.away_score:
        winner = match.home_team
    elif match.away_score > match.home_score:
        winner = match.away_team
    else:
        winner = None  # seri

    # Evaluasi semua prediksi untuk pertandingan ini
    predictions = Prediction.objects.filter(match=match)
    for pred in predictions:
        if winner and pred.predicted_winner == winner:
            pred.points_awarded = 10
        else:
            pred.points_awarded = 0
        pred.save()

    return JsonResponse({'success': True, 'message': f'Prediksi untuk {match} sudah dievaluasi.'})


# ================================
# 4️⃣ Leaderboard untuk turnamen
# ================================
def leaderboard_view(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)

    # Hitung total poin per user dalam turnamen
    leaderboard = (
        Prediction.objects.filter(match__tournament=tournament)
        .values('user__username')
        .annotate(total_points=Sum('points_awarded'))
        .order_by('-total_points')
    )

    context = {
        'tournament': tournament,
        'leaderboard': leaderboard,
    }
    return render(request, 'predictions/leaderboard.html', context)
