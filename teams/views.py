from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from .models import Team


def show_main_teams(request):
    """Halaman utama Teams"""
    teams = Team.objects.all()
    return render(request, 'teams.html', {'teams': teams})

def manage_team(request):
    """Halaman manage team"""
    return render(request, 'manage_team.html')

def meet_team(request):
    """Halaman meet team"""
    return render(request, 'meet_team.html')

def join_team_page(request):
    """Halaman join team"""
    return render(request, 'join_team.html')
# ======== SEARCH / VIEW (tidak perlu login) ========

@csrf_exempt
def search_teams(request):
    """Search tim untuk modal join"""
    query = request.GET.get('q', '').strip()
    teams = Team.objects.all()

    if request.user.is_authenticated:
        # Kecualikan tim yang sudah diikuti
        teams = teams.exclude(members=request.user)

    if query:
        teams = teams.filter(Q(name__icontains=query) | Q(captain__username__icontains=query))

    paginator = Paginator(teams, 5)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    results = [
        {
            'id': team.id,
            'name': team.name,
            'logo': team.logo.url if team.logo else None,
            'captain': team.captain.username if team.captain else None,
            'members_count': team.members.count(),
        }
        for team in page_obj
    ]

    return JsonResponse({'status': 'success', 'results': results})


@csrf_exempt
def search_meet_teams(request):
    """Tim yang user ikuti (untuk modal meet)"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'success', 'results': []})

    teams = Team.objects.filter(members=request.user)
    query = request.GET.get('q', '').strip()

    if query:
        teams = teams.filter(Q(name__icontains=query) | Q(captain__username__icontains=query))

    results = [
        {
            'id': team.id,
            'name': team.name,
            'logo': team.logo.url if team.logo else None,
            'captain': team.captain.username if team.captain else None,
            'members_count': team.members.count(),
        }
        for team in teams
    ]
    return JsonResponse({'status': 'success', 'results': results})


@csrf_exempt
def search_managed_teams(request):
    """Tim yang dikapteni user (untuk modal manage)"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'success', 'results': []})

    teams = Team.objects.filter(captain=request.user)
    query = request.GET.get('q', '').strip()

    if query:
        teams = teams.filter(name__icontains=query)

    results = [
        {
            'id': team.id,
            'name': team.name,
            'logo': team.logo.url if team.logo else None,
            'members_count': team.members.count(),
        }
        for team in teams
    ]
    return JsonResponse({'status': 'success', 'results': results})


# ======== ACTIONS (harus login) ========

@require_POST
@login_required
def create_team(request):
    name = request.POST.get('name')
    logo = request.FILES.get('logo')

    if not name:
        return JsonResponse({'status': 'error', 'message': 'Nama tim wajib diisi.'}, status=400)

    team = Team.objects.create(name=name, captain=request.user, logo=logo)
    team.members.add(request.user)
    return JsonResponse({'status': 'success', 'team_id': team.id})


@require_POST
@login_required
def edit_team(request, team_id):
    team = get_object_or_404(Team, id=team_id, captain=request.user)
    name = request.POST.get('name')
    logo = request.FILES.get('logo')

    if name:
        team.name = name
    if logo:
        team.logo = logo
    team.save()

    return JsonResponse({'status': 'success'})


@require_POST
@login_required
def delete_team(request, team_id):
    team = get_object_or_404(Team, id=team_id, captain=request.user)
    team.delete()
    return JsonResponse({'status': 'success'})


@require_POST
@login_required
def join_team(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    team.members.add(request.user)
    return JsonResponse({'status': 'success'})


@require_POST
@login_required
def leave_team(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    team.members.remove(request.user)
    return JsonResponse({'status': 'success'})


@require_POST
@login_required
def delete_member(request, team_id, member_id):
    team = get_object_or_404(Team, id=team_id, captain=request.user)
    member = get_object_or_404(team.members, id=member_id)

    if member == request.user:
        return JsonResponse({'status': 'error', 'message': 'Kapten tidak dapat menghapus diri sendiri.'}, status=400)

    team.members.remove(member)
    return JsonResponse({'status': 'success', 'removed_member': member.username})

def show_json(request):
    teams = Team.objects.all()
    data = []
    for team in teams:
        data.append({
            'id': team.id,
            'name': team.name,
            'logo': team.logo.url if team.logo else None,
            'captain': team.captain.username if team.captain else None,
            'members': [member.username for member in team.members.all()],
        })
    return JsonResponse(data, safe=False)
