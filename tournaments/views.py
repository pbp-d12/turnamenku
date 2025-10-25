from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.urls import reverse
from django.db import models
from django.db.models import Prefetch, Q, Count, Sum, F, Case, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import traceback 

from .models import Tournament, Match
from .forms import TournamentForm
from teams.models import Team

def tournament_home(request):
    create_form = TournamentForm()
    context = {
        'create_form': create_form
    }
    return render(request, 'tournaments/tournament_list.html', context)

def get_tournaments_json(request):
    queryset = Tournament.objects.select_related('organizer').all()
    today = timezone.now().date()
    
    #   Filtering   
    status_filter = request.GET.get('status', None)
    search_query = request.GET.get('search', None)

    if status_filter:
        if status_filter == 'upcoming':
            queryset = queryset.filter(start_date__gt=today)
        elif status_filter == 'ongoing':
            queryset = queryset.filter(start_date__lte=today, end_date__gte=today)
        elif status_filter == 'past':
            queryset = queryset.filter(end_date__lt=today)

    if search_query:
        queryset = queryset.filter(Q(name__icontains=search_query))

    #   Ordering   
    tournaments_list = queryset.order_by('-start_date', 'name')
    
    #   Pagination Logic  
    PER_PAGE = 9 
    page_number = request.GET.get('page', 1)
    paginator = Paginator(tournaments_list, PER_PAGE)
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    #   Serialization (now on page_obj)  
    data = []
    for t in page_obj: # Iterate over the paginated results
        data.append({
            'id': t.pk,
            'name': t.name,
            'description': t.description[:100] + '...' if t.description and len(t.description) > 100 else t.description,
            'organizer': t.organizer.username,
            'start_date': t.start_date.strftime('%d %b %Y'),
            'end_date': t.end_date.strftime('%d %b %Y'),
            'banner_url': t.banner,
            'detail_page_url': reverse('tournaments:tournament_detail_page', args=[t.pk])
        })
    
    #   Return new JSON object structure  
    return JsonResponse({
        'tournaments': data,
        'has_next_page': page_obj.has_next(),
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
    })

@login_required
@require_POST
def create_tournament(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ['PENYELENGGARA', 'ADMIN']:
        return JsonResponse({
            'status': 'error',
            'message': 'Akses ditolak: Hanya Penyelenggara atau Admin yang dapat membuat turnamen.'
        }, status=403)

    form = TournamentForm(request.POST)

    if form.is_valid():
        tournament = form.save(commit=False)
        tournament.organizer = request.user
        tournament.save()
        form.save_m2m()

        return JsonResponse({
            'status': 'success',
            'message': 'Turnamen berhasil dibuat!',
            'tournament': {
                'id': tournament.pk,
                'name': tournament.name,
                'description': tournament.description[:100] + '...' if tournament.description and len(tournament.description) > 100 else tournament.description,
                'organizer': tournament.organizer.username,
                'start_date': tournament.start_date.strftime('%d %b %Y'),
                'end_date': tournament.end_date.strftime('%d %b %Y'),
                'banner_url': tournament.banner,
                'detail_page_url': reverse('tournaments:tournament_detail_page', args=[tournament.pk])
            }
        }, status=201)
    else:
        errors_dict = form.errors.get_json_data(escape_html=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Gagal membuat turnamen. Periksa input Anda.',
            'errors': errors_dict
        }, status=400)

def tournament_detail_page(request, tournament_id):
    get_object_or_404(Tournament, pk=tournament_id)
    edit_form = TournamentForm()
    context = {
        'tournament_id': tournament_id,
        'edit_form': edit_form
    }
    return render(request, 'tournaments/tournament_detail.html', context)

def get_tournament_detail_json(request, tournament_id):
    try:
        tournament = get_object_or_404(
            Tournament.objects.select_related('organizer').prefetch_related(
                Prefetch('matches', queryset=Match.objects.select_related('home_team', 'away_team').order_by('match_date')),
                Prefetch('participants', queryset=Team.objects.all().order_by('name'))
            ),
            pk=tournament_id
        )

        match_data = []
        for match in tournament.matches.all(): 
            local_match_time = timezone.localtime(match.match_date)
            is_finished = match.home_score is not None and match.away_score is not None
            
            match_data.append({
                'id': match.pk,
                'home_team_name': match.home_team.name,
                'away_team_name': match.away_team.name,
                'match_date_formatted': local_match_time.strftime('%d %b %Y, %H:%M %Z'),
                'home_score': match.home_score,
                'away_score': match.away_score,
                'is_finished': is_finished
            })
        home_win = Q(home_score__gt=F('away_score'))
        home_draw = Q(home_score=F('away_score'))
        home_loss = Q(home_score__lt=F('away_score'))
        
        away_win = Q(away_score__gt=F('home_score'))
        away_draw = Q(away_score=F('home_score'))
        away_loss = Q(away_score__lt=F('home_score'))

        home_matches = Match.objects.filter(
            home_team=models.OuterRef('pk'),
            tournament=tournament,
            home_score__isnull=False
        ).values('home_team') 

        home_wins_sub = home_matches.annotate(c=Count('pk', filter=home_win)).values('c')
        home_draws_sub = home_matches.annotate(c=Count('pk', filter=home_draw)).values('c')
        home_losses_sub = home_matches.annotate(c=Count('pk', filter=home_loss)).values('c')
        home_gf_sub = home_matches.annotate(s=Sum('home_score')).values('s')
        home_ga_sub = home_matches.annotate(s=Sum('away_score')).values('s')

        away_matches = Match.objects.filter(
            away_team=models.OuterRef('pk'),
            tournament=tournament,
            home_score__isnull=False
        ).values('away_team') 

        away_wins_sub = away_matches.annotate(c=Count('pk', filter=away_win)).values('c')
        away_draws_sub = away_matches.annotate(c=Count('pk', filter=away_draw)).values('c')
        away_losses_sub = away_matches.annotate(c=Count('pk', filter=away_loss)).values('c')
        away_gf_sub = away_matches.annotate(s=Sum('away_score')).values('s')
        away_ga_sub = away_matches.annotate(s=Sum('home_score')).values('s')

        leaderboard_queryset = tournament.participants.all().annotate(
            h_wins=Coalesce(models.Subquery(home_wins_sub, output_field=models.IntegerField()), 0),
            h_draws=Coalesce(models.Subquery(home_draws_sub, output_field=models.IntegerField()), 0),
            h_losses=Coalesce(models.Subquery(home_losses_sub, output_field=models.IntegerField()), 0),
            h_gf=Coalesce(models.Subquery(home_gf_sub, output_field=models.IntegerField()), 0),
            h_ga=Coalesce(models.Subquery(home_ga_sub, output_field=models.IntegerField()), 0),
            
            a_wins=Coalesce(models.Subquery(away_wins_sub, output_field=models.IntegerField()), 0),
            a_draws=Coalesce(models.Subquery(away_draws_sub, output_field=models.IntegerField()), 0),
            a_losses=Coalesce(models.Subquery(away_losses_sub, output_field=models.IntegerField()), 0),
            a_gf=Coalesce(models.Subquery(away_gf_sub, output_field=models.IntegerField()), 0),
            a_ga=Coalesce(models.Subquery(away_ga_sub, output_field=models.IntegerField()), 0),
        
        ).annotate(
            wins=F('h_wins') + F('a_wins'),
            draws=F('h_draws') + F('a_draws'),
            losses=F('h_losses') + F('a_losses'),
            goals_for=F('h_gf') + F('a_gf'),
            goals_against=F('h_ga') + F('a_ga')
        ).annotate(
            played=F('wins') + F('draws') + F('losses'),
            goal_difference=F('goals_for') - F('goals_against'),
            points=(F('wins') * 3) + F('draws')
        ).order_by(
            '-points', 
            '-goal_difference', 
            '-goals_for', 
            'name'
        ).values(
            team_id=F('id'), 
            team_name=F('name'), 
            team_logo=F('logo'),
            played=F('played'), 
            wins=F('wins'), 
            draws=F('draws'), 
            losses=F('losses'), 
            goals_for=F('goals_for'), 
            goals_against=F('goals_against'), 
            goal_difference=F('goal_difference'), 
            points=F('points')
        )
        
        leaderboard_data = list(leaderboard_queryset)

        participant_data = [
            {'id': team.pk, 'name': team.name, 'logo_url': team.logo if team.logo else None}
            for team in tournament.participants.all()
        ]

        print(f"DEBUG: Participant data for tournament {tournament_id}: {participant_data}")
        print(f"DEBUG: Leaderboard data for tournament {tournament_id}: {leaderboard_data}")


        is_organizer_or_admin = False
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            is_admin = profile and profile.role == 'ADMIN'
            is_organizer = request.user == tournament.organizer
            is_organizer_or_admin = is_admin or is_organizer

        data = {
            'id': tournament.pk,
            'name': tournament.name,
            'description': tournament.description,
            'organizer_username': tournament.organizer.username,
            'organizer_profile_url': reverse('main:profile', args=[tournament.organizer.username]),
            'start_date_formatted': tournament.start_date.strftime('%d %b %Y'),
            'end_date_formatted': tournament.end_date.strftime('%d %b %Y'),
            'start_date_raw': tournament.start_date.strftime('%Y-%m-%d'),
            'end_date_raw': tournament.end_date.strftime('%Y-%m-%d'),
            'banner_url': tournament.banner,
            'matches': match_data,
            'participants': participant_data,
            'leaderboard': leaderboard_data, 
            'registration_open': tournament.registration_open, 
            'winner_name': tournament.winner.name if tournament.winner else None, 
            'forum_url': reverse('forums:forum_threads', args=[tournament.pk]),
            'predictions_url': f"{reverse('predictions:predictions_index')}?tournament={tournament.pk}",
            'is_organizer_or_admin': is_organizer_or_admin
        }
        return JsonResponse(data)

    except Http404:
        return JsonResponse({'error': 'Tournament not found'}, status=404)
    except Exception as e:
        print(f"!!! ERROR in get_tournament_detail_json for ID {tournament_id}: {type(e).__name__} - {e}")
        traceback.print_exc()
        return JsonResponse({'error': 'An unexpected server error occurred'}, status=500)


@login_required
@require_POST
def edit_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)

    profile = getattr(request.user, 'profile', None)
    is_admin = profile and profile.role == 'ADMIN'
    is_organizer = request.user == tournament.organizer

    if not (is_organizer or is_admin):
        return JsonResponse({
            'status': 'error',
            'message': 'Akses ditolak: Hanya organizer atau admin yang dapat mengedit turnamen ini.'
        }, status=403)

    form = TournamentForm(request.POST, instance=tournament)

    if form.is_valid():
        # save() handles regular fields and returns the instance
        updated_tournament = form.save()
        # save_m2m() is needed for ManyToManyFields after saving the instance
        # form.save_m2m() # This is handled automatically by form.save() if commit=True (default)

        participant_data = [
             {'id': team.pk, 'name': team.name, 'logo_url': team.logo if team.logo else None}
             for team in updated_tournament.participants.all().order_by('name')
        ]

        match_data = []
        for match in updated_tournament.matches.select_related('home_team', 'away_team').order_by('match_date'):
             local_match_time = timezone.localtime(match.match_date)
             match_data.append({
                 'id': match.pk,
                 'home_team_name': match.home_team.name,
                 'away_team_name': match.away_team.name,
                 'match_date_formatted': local_match_time.strftime('%d %b %Y, %H:%M %Z'),
                 'home_score': match.home_score,
                 'away_score': match.away_score,
                 'is_finished': match.home_score is not None and match.away_score is not None
             })

        return JsonResponse({
            'status': 'success',
            'message': 'Turnamen berhasil diperbarui!',
            'tournament': {
                'id': updated_tournament.pk,
                'name': updated_tournament.name,
                'description': updated_tournament.description,
                'organizer_username': updated_tournament.organizer.username,
                'organizer_profile_url': reverse('main:profile', args=[updated_tournament.organizer.username]),
                'start_date_formatted': updated_tournament.start_date.strftime('%d %b %Y'),
                'end_date_formatted': updated_tournament.end_date.strftime('%d %b %Y'),
                'start_date_raw': updated_tournament.start_date.strftime('%Y-%m-%d'),
                'end_date_raw': updated_tournament.end_date.strftime('%Y-%m-%d'),
                'banner_url': updated_tournament.banner,
                'matches': match_data,
                'participants': participant_data,
                'registration_open': updated_tournament.registration_open, # Include updated status
                'winner_name': updated_tournament.winner.name if updated_tournament.winner else None, # Include winner
                'forum_url': reverse('forums:forum_threads', args=[updated_tournament.pk]),
                'predictions_url': f"{reverse('predictions:predictions_index')}?tournament={updated_tournament.pk}",
                'is_organizer_or_admin': True
            }
        }, status=200)
    else:
        errors_dict = form.errors.get_json_data(escape_html=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Gagal memperbarui. Periksa input Anda.',
            'errors': errors_dict
        }, status=400)

@login_required
@require_http_methods(["DELETE"])
def delete_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)

    profile = getattr(request.user, 'profile', None)
    is_admin = profile and profile.role == 'ADMIN'
    is_organizer = request.user == tournament.organizer

    if not (is_organizer or is_admin):
        return JsonResponse({
            'status': 'error',
            'message': 'Akses ditolak: Hanya organizer atau admin yang dapat menghapus turnamen ini.'
        }, status=403)

    try:
        tournament_name = tournament.name
        tournament.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'Turnamen "{tournament_name}" berhasil dihapus.',
            'redirect_url': reverse('tournaments:tournament_home')
        }, status=200)
    except Exception as e:
        print(f"Error deleting tournament: {e}")
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': 'Terjadi kesalahan saat mencoba menghapus turnamen.'
        }, status=500)
    

@login_required
@require_POST
def register_team_view(request, tournament_id):
    """Adds the user's captained team to the tournament participants."""
    tournament = get_object_or_404(Tournament, pk=tournament_id)

    if not tournament.registration_open:
        return JsonResponse({'status': 'error', 'message': 'Pendaftaran untuk turnamen ini sudah ditutup.'}, status=400)

    try:
        team_to_register = Team.objects.get(captain=request.user)
    except Team.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Anda bukan kapten tim manapun.'}, status=403)
    except Team.MultipleObjectsReturned:
         team_to_register = Team.objects.filter(captain=request.user).first()

    if tournament.participants.filter(pk=team_to_register.pk).exists():
        return JsonResponse({'status': 'error', 'message': f'Tim "{team_to_register.name}" sudah terdaftar.'}, status=400)

    tournament.participants.add(team_to_register)

    return JsonResponse({
        'status': 'success',
        'message': f'Tim "{team_to_register.name}" berhasil didaftarkan!'
    }, status=200)


def get_user_captain_status(request, tournament_id):
    """Checks which teams the logged-in user captains and if they can register for this tournament."""
    tournament = get_object_or_404(Tournament, pk=tournament_id)

    eligible_teams = []
    if request.user.is_authenticated:
        captained_teams = Team.objects.filter(captain=request.user)
        if captained_teams.exists():
            registered_team_ids = tournament.participants.values_list('id', flat=True)
            for team in captained_teams:
                if team.id not in registered_team_ids:
                    eligible_teams.append({
                        'id': team.id,
                        'name': team.name
                    })

    can_register = tournament.registration_open and len(eligible_teams) > 0

    return JsonResponse({
        'can_register': can_register,
        'eligible_teams': eligible_teams, 
        'is_registration_open': tournament.registration_open
    })

@login_required 
def search_teams_json(request):
    query = request.GET.get('q', '').strip()
    teams = []
    if len(query) >= 2: 
        teams = Team.objects.filter(name__icontains=query).order_by('name')[:10] 
    data = [{'id': team.pk, 'name': team.name} for team in teams]
    return JsonResponse(data, safe=False)