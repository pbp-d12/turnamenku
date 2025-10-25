from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Q
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from datetime import datetime
import json
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator  
from predictions.models import Prediction
from tournaments.models import Match, Tournament
from teams.models import Team


def predictions_index(request):
    tournament_id = request.GET.get('tournament')
    
    
    tournaments = Tournament.objects.prefetch_related('participants').all().order_by('name')
    
    tournaments_with_teams = {}
    for t in tournaments:
        teams_list = list(t.participants.all().order_by('name').values('id', 'name'))
        tournaments_with_teams[t.id] = teams_list
    
    context = {
        'tournaments': tournaments,
        'tournaments_with_teams_json': mark_safe(json.dumps(tournaments_with_teams)),
        'current_tournament_id': tournament_id if tournament_id else "",
    }
    return render(request, 'predictions/predictions_index.html', context)

#Untuk mengambil partial HTML ongoing matches
def get_ongoing_matches(request):
    tournament_id = request.GET.get('tournament')
    matches = Match.objects.all()
    if tournament_id:
        matches = matches.filter(tournament_id=tournament_id)
    
    ongoing_matches_list = matches.filter(  
        Q(home_score__isnull=True) | Q(away_score__isnull=True)
    ).order_by('match_date')
    
   
    paginator = Paginator(ongoing_matches_list, 9) 
    page_number = request.GET.get('page')
    ongoing_matches_page = paginator.get_page(page_number)

    
    context = {'ongoing_matches': ongoing_matches_page} 
    return render(request, 'predictions/_ongoing_matches_partial.html', context)

#Untuk mengambil partial HTML finished matches
def get_finished_matches(request):
    tournament_id = request.GET.get('tournament')
    matches = Match.objects.all()
    if tournament_id:
        matches = matches.filter(tournament_id=tournament_id)

    finished_matches_list = matches.filter( 
        home_score__isnull=False, away_score__isnull=False
    ).order_by('-match_date')
    

    paginator = Paginator(finished_matches_list, 9) 
    page_number = request.GET.get('page')
    finished_matches_page = paginator.get_page(page_number)

    
    context = {'finished_matches': finished_matches_page} 
    return render(request, 'predictions/_finished_matches_partial.html', context)

@login_required
def add_match(request):
    if request.user.profile.role not in ('PENYELENGGARA', 'ADMIN'):
        return JsonResponse({'success': False, 'message': 'Kamu tidak punya izin.'}, status=403)

    if request.method == 'POST':
        tournament = get_object_or_404(Tournament, id=request.POST['tournament'])
        home_team = get_object_or_404(Team, id=request.POST['home_team'])
        away_team = get_object_or_404(Team, id=request.POST['away_team'])
        
        # Validasi menggunakan 'tournament.participants.all()'
        tournament_teams = tournament.participants.all()
        if home_team not in tournament_teams or away_team not in tournament_teams:
            return JsonResponse({'success': False, 'message': 'Tim yang dipilih tidak terdaftar di turnamen ini.'}, status=400)
        
        if home_team == away_team:
             return JsonResponse({'success': False, 'message': 'Tim Home dan Tim Away tidak boleh sama.'}, status=400)

        # parse datetime-local
        match_date_str = request.POST['match_date']
        match_date = datetime.strptime(match_date_str, "%Y-%m-%dT%H:%M")

        Match.objects.create(
            tournament=tournament,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date
        )
        return JsonResponse({'success': True, 'message': 'Match berhasil ditambahkan!'})
    return JsonResponse({'success': False, 'message': 'Metode tidak valid.'}, status=400)


@login_required
def submit_prediction(request):
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
            'message': f'Berhasil voting untuk {team.name}!',
        })

    return JsonResponse({'success': False, 'message': 'Permintaan tidak valid.'}, status=400)


def leaderboard_view(request):
    sort_order = request.GET.get('sort', 'desc')  

    leaderboard = (
        Prediction.objects.values('user__username')
        .annotate(total_points=Sum('points_awarded'))
        .order_by('-total_points' if sort_order == 'desc' else 'total_points')
    )

    context = {
        'leaderboard': leaderboard,
        'sort_order': sort_order
    }
    return render(request, 'predictions/leaderboard.html', context)


@login_required
def evaluate_predictions(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    if match.home_score is None or match.away_score is None:
        return JsonResponse({'success': False, 'message': 'Pertandingan belum selesai.'}, status=400)

    if match.home_score > match.away_score:
        correct_team = match.home_team
    elif match.away_score > match.home_score:
        correct_team = match.away_team
    else:
        correct_team = None

    predictions = Prediction.objects.filter(match=match)
    for p in predictions:
        if correct_team is None:
            # Jika hasilnya draw
            p.points_awarded = 0
        elif p.predicted_winner == correct_team:
            # Prediksi benar
            p.points_awarded = 10
        else:
            # Prediksi salah
            p.points_awarded = -10
        p.save()

    return JsonResponse({'success': True, 'message': 'Prediksi telah dievaluasi!'})


def get_match_scores(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    return JsonResponse({
        "home_score": match.home_score,
        "away_score": match.away_score
    })


@require_POST
def edit_match_score(request):
    match_id = request.POST.get("match_id")
    home_score = request.POST.get("home_score")
    away_score = request.POST.get("away_score")
    match = get_object_or_404(Match, id=match_id)

    # cast ke int
    match.home_score = int(home_score)
    match.away_score = int(away_score)
    match.save()

    return JsonResponse({"success": True, "message": "Skor berhasil diperbarui"})

@login_required
def delete_prediction(request):
    if request.user.profile.role not in ('PENYELENGGARA', 'ADMIN'):
        return JsonResponse({'success': False, 'message': 'Kamu tidak punya izin.'}, status=403)
    
    if request.method == 'POST':
        match_id = request.POST.get('match_id')

        # Hapus semua prediksi untuk match tersebut
        deleted_count, _ = Prediction.objects.filter(match_id=match_id).delete()

        if deleted_count:
            return JsonResponse({'success': True, 'message': 'Prediksi berhasil dihapus!'})
        else:
            return JsonResponse({'success': False, 'message': 'Prediksi tidak ditemukan.'})
    
    return JsonResponse({'success': False, 'message': 'Metode tidak valid.'}, status=400)