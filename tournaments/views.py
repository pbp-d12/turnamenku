from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.db.models import Prefetch
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .models import Tournament, Match
from .forms import TournamentForm


def tournament_home(request):
    """
    Renders the main page for tournaments, which includes the
    'Create Tournament' modal form for eligible users.
    """
    create_form = TournamentForm() # Instantiate form for the modal
    context = {
        'create_form': create_form
    }
    return render(request, 'tournaments/tournament_list.html', context)

def get_tournaments_json(request):
    """
    Returns a JSON list of tournaments, applying filters based on GET parameters.
    Filters:
        - status (upcoming, ongoing, past)
        - search (by name)
    """
    queryset = Tournament.objects.select_related('organizer').all()
    today = timezone.now().date()

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

    tournaments = queryset.order_by('-start_date', 'name') 
    
    data = []
    for t in tournaments:
        data.append({
            'id': t.pk,
            'name': t.name,
            'description': t.description[:100] + '...' if t.description and len(t.description) > 100 else t.description,
            'organizer': t.organizer.username,
            'start_date': t.start_date.strftime('%d %b %Y'),
            'end_date': t.end_date.strftime('%d %b %Y'),
            'banner_url': t.banner.url if t.banner else None,
            'detail_page_url': reverse('tournaments:tournament_detail_page', args=[t.pk])
        })
    return JsonResponse(data, safe=False)

@login_required
@require_POST
def create_tournament(request):
    """
    Handles AJAX POST request to create a new tournament.
    Restricted to 'PENYELENGGARA' and 'ADMIN' roles.
    """
    # Role Check: User must have a profile and be an Organizer or Admin
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ['PENYELENGGARA', 'ADMIN']:
        return JsonResponse({
            'status': 'error', 
            'message': 'Akses ditolak: Hanya Penyelenggara atau Admin yang dapat membuat turnamen.'
        }, status=403) # 403 Forbidden

    form = TournamentForm(request.POST, request.FILES)
    if form.is_valid():
        tournament = form.save(commit=False)
        tournament.organizer = request.user # Set organizer to the logged-in user
        tournament.save()
        
        # Return data for the newly created tournament
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
                'banner_url': tournament.banner.url if tournament.banner else None,
                'detail_page_url': reverse('tournaments:tournament_detail_page', args=[tournament.pk])
            }
        }, status=201) # 201 Created
    else:
        # Return form validation errors
        errors_dict = form.errors.get_json_data(escape_html=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Gagal membuat turnamen. Periksa input Anda.',
            'errors': errors_dict
        }, status=400) # 400 Bad Request

def tournament_detail_page(request, tournament_id):
    """
    Renders the HTML shell for the tournament detail page.
    Passes the ID to the template for AJAX fetching.
    """
    # Ensure the tournament exists before rendering the page
    get_object_or_404(Tournament, pk=tournament_id)
    context = {
        'tournament_id': tournament_id
    }
    return render(request, 'tournaments/tournament_detail.html', context)

def get_tournament_detail_json(request, tournament_id):
    """
    Returns detailed JSON data for a single tournament, including matches.
    """
    try:
        # Optimized query to get tournament, organizer, and all related matches+teams
        tournament = get_object_or_404(
            Tournament.objects.select_related('organizer').prefetch_related(
                Prefetch('matches', queryset=Match.objects.select_related('home_team', 'away_team').order_by('match_date'))
            ),
            pk=tournament_id
        )

        # Serialize match data
        match_data = []
        for match in tournament.matches.all():
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

        # Serialize main tournament data
        data = {
            'id': tournament.pk,
            'name': tournament.name,
            'description': tournament.description,
            'organizer_username': tournament.organizer.username,
            'organizer_profile_url': reverse('main:profile', args=[tournament.organizer.username]),
            'start_date_formatted': tournament.start_date.strftime('%d %b %Y'),
            'end_date_formatted': tournament.end_date.strftime('%d %b %Y'),
            'banner_url': tournament.banner.url if tournament.banner else None,
            'matches': match_data,
            # Add URLs for related actions
            'forum_url': reverse('forums:forum_threads', args=[tournament.pk]),
            'predictions_url': f"{reverse('predictions:predictions_index')}?tournament={tournament.pk}"
        }
        return JsonResponse(data)

    except Tournament.DoesNotExist:
        return JsonResponse({'error': 'Tournament not found'}, status=404)
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching tournament detail JSON: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
