from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.urls import reverse
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect

from .models import Tournament, Match
from .forms import TournamentForm


def tournament_home(request):
    """
    Merender halaman HTML utama untuk turnamen,
    termasuk form modal 'Buat Turnamen'.
    """
    create_form = TournamentForm()
    context = {
        'create_form': create_form
    }
    return render(request, 'tournaments/tournament_list.html', context)

def get_tournaments_json(request):
    """
    Mengembalikan daftar turnamen dalam format JSON, menerapkan filter
    berdasarkan parameter GET.
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
            'banner_url': t.banner, # Menggunakan URLField
            'detail_page_url': reverse('tournaments:tournament_detail_page', args=[t.pk])
        })
    return JsonResponse(data, safe=False)

@login_required
@require_POST
def create_tournament(request):
    """
    Menangani request POST AJAX untuk membuat turnamen baru.
    Dibatasi untuk role 'PENYELENGGARA' dan 'ADMIN'.
    """
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ['PENYELENGGARA', 'ADMIN']:
        return JsonResponse({
            'status': 'error',
            'message': 'Akses ditolak: Hanya Penyelenggara atau Admin yang dapat membuat turnamen.'
        }, status=403)

    form = TournamentForm(request.POST) # Tidak perlu request.FILES untuk URLField

    if form.is_valid():
        tournament = form.save(commit=False)
        tournament.organizer = request.user
        tournament.save()

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
                'banner_url': tournament.banner, # Menggunakan URLField
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
    """
    Merender shell HTML untuk halaman detail turnamen.
    Juga mengirimkan form *edit* (kosong) untuk modal.
    """
    get_object_or_404(Tournament, pk=tournament_id)
    # Kirim instance form KOSONG, akan diisi oleh AJAX
    edit_form = TournamentForm()
    context = {
        'tournament_id': tournament_id,
        'edit_form': edit_form # Kirim form ke template
    }
    return render(request, 'tournaments/tournament_detail.html', context)

def get_tournament_detail_json(request, tournament_id):
    """
    Mengembalikan data JSON detail untuk satu turnamen, termasuk data pertandingan
    dan status kepemilikan.
    """
    try:
        # get_object_or_404 sekarang di dalam try block
        tournament = get_object_or_404(
            Tournament.objects.select_related('organizer').prefetch_related(
                Prefetch('matches', queryset=Match.objects.select_related('home_team', 'away_team').order_by('match_date'))
            ),
            pk=tournament_id
        )

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

        # Cek status kepemilikan/admin
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
            'start_date_raw': tournament.start_date.strftime('%Y-%m-%d'), # Untuk pre-fill form
            'end_date_raw': tournament.end_date.strftime('%Y-%m-%d'),   # Untuk pre-fill form
            'banner_url': tournament.banner, # Menggunakan URLField
            'matches': match_data,
            'forum_url': reverse('forums:forum_threads', args=[tournament.pk]),
            'predictions_url': f"{reverse('predictions:predictions_index')}?tournament={tournament.pk}",
            'is_organizer_or_admin': is_organizer_or_admin # Kirim status kepemilikan
        }
        return JsonResponse(data)

    # --- Tangkap Http404 secara eksplisit ---
    except Http404:
        return JsonResponse({'error': 'Tournament not found'}, status=404)
    # ----------------------------------------
    except Exception as e:
        print(f"Error fetching tournament detail JSON: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@login_required
@require_POST
def edit_tournament(request, tournament_id):
    """
    Menangani request POST AJAX untuk mengedit turnamen yang ada.
    """
    tournament = get_object_or_404(Tournament, pk=tournament_id)

    # Pengecekan Keamanan
    profile = getattr(request.user, 'profile', None)
    is_admin = profile and profile.role == 'ADMIN'
    is_organizer = request.user == tournament.organizer

    if not (is_organizer or is_admin):
        return JsonResponse({
            'status': 'error',
            'message': 'Akses ditolak: Hanya organizer atau admin yang dapat mengedit turnamen ini.'
        }, status=403) # 403 Forbidden

    # Gunakan 'instance=tournament' untuk memberi tahu form bahwa ini adalah update
    form = TournamentForm(request.POST, instance=tournament)

    if form.is_valid():
        updated_tournament = form.save()

        # Kembalikan data yang sudah diperbarui agar frontend bisa refresh
        # Kita juga perlu mengirim 'is_organizer_or_admin' lagi
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
                'matches': list(updated_tournament.matches.select_related('home_team', 'away_team').order_by('match_date').values(
                    'pk', 'home_team__name', 'away_team__name', 'match_date', 'home_score', 'away_score'
                )), # Kirim ulang data match (meskipun tidak berubah)
                'forum_url': reverse('forums:forum_threads', args=[updated_tournament.pk]),
                'predictions_url': f"{reverse('predictions:predictions_index')}?tournament={updated_tournament.pk}",
                'is_organizer_or_admin': True # Jika bisa edit, pasti true
            }
        }, status=200)
    else:
        # Kembalikan error validasi form
        errors_dict = form.errors.get_json_data(escape_html=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Gagal memperbarui. Periksa input Anda.',
            'errors': errors_dict
        }, status=400)

@login_required
@require_http_methods(["DELETE"]) # Hanya izinkan metode DELETE
def delete_tournament(request, tournament_id):
    """
    Menangani request DELETE AJAX untuk menghapus turnamen yang ada.
    Dibatasi untuk organizer atau admin.
    """
    tournament = get_object_or_404(Tournament, pk=tournament_id)

    # Pengecekan Keamanan (sama seperti edit)
    profile = getattr(request.user, 'profile', None)
    is_admin = profile and profile.role == 'ADMIN'
    is_organizer = request.user == tournament.organizer

    if not (is_organizer or is_admin):
        return JsonResponse({
            'status': 'error',
            'message': 'Akses ditolak: Hanya organizer atau admin yang dapat menghapus turnamen ini.'
        }, status=403) # 403 Forbidden

    try:
        tournament_name = tournament.name # Simpan nama untuk pesan
        tournament.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'Turnamen "{tournament_name}" berhasil dihapus.',
            # Kirim URL redirect agar JS bisa mengarahkan pengguna
            'redirect_url': reverse('tournaments:tournament_home')
        }, status=200)
    except Exception as e:
        # Tangkap error tak terduga saat menghapus
        print(f"Error deleting tournament: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Terjadi kesalahan saat mencoba menghapus turnamen.'
        }, status=500)
