from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage
from django.views.decorators.csrf import csrf_exempt
from .models import Team


def show_main_teams(request):
    teams = Team.objects.all()
    user = request.user if request.user.is_authenticated else None
    return render(request, 'teams.html', {'teams': teams, 'user': user})

@csrf_exempt
def search_teams(request):
    """
    Search tim untuk berbagai mode:
      - mode=join   : semua tim (kecuali yang sudah diikuti user)
      - mode=meet   : tim yang user ikuti
      - mode=manage : tim yang dikapteni user
    Query param:
      ?mode=join&q=abc&page=2
    """
    query = request.GET.get('q', '').strip()
    mode = request.GET.get('mode', 'join')
    page = request.GET.get('page', 1)

    # Base queryset
    teams = Team.objects.all().annotate(members_count=Count('members'))

    if request.user.is_authenticated:
        if mode == 'join':
            teams = teams.exclude(members=request.user)
        elif mode == 'meet':
            teams = teams.filter(members=request.user)
        elif mode == 'manage':
            if request.user.is_superuser:
                teams = teams
            else:
                teams = teams.filter(captain=request.user)
        else:
            return JsonResponse({'status': 'error', 'message': 'Mode tidak valid.'}, status=400)
    else:
        if mode != 'join':
            return JsonResponse({'status': 'error', 'message': 'Login diperlukan.'}, status=401)

    if query:
        teams = teams.filter(
            Q(name__icontains=query) | Q(captain__username__icontains=query)
        )

    # Pagination
    paginator = Paginator(teams, 5)
    try:
        page_obj = paginator.get_page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Format hasil JSON
    results = [
        {
            'id': team.id,
            'name': team.name,
            'logo': team.logo.url if team.logo else None,
            'captain': team.captain.username if team.captain else None,
            'members_count': team.members_count,
        }
        for team in page_obj
    ]

    return JsonResponse({
        'status': 'success',
        'mode': mode,
        'results': results,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })

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
def join_team(request, team_id):
    team = get_object_or_404(Team, id=team_id)

    if request.user in team.members.all():
        return JsonResponse({'status': 'error', 'message': 'Anda sudah menjadi anggota tim ini.'}, status=400)

    team.members.add(request.user)
    return JsonResponse({'status': 'success'})

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
def delete_member(request, team_id, member_id):
    team = get_object_or_404(Team, id=team_id, captain=request.user)
    member = get_object_or_404(team.members.all(), id=member_id)

    if member == request.user:
        return JsonResponse({'status': 'error', 'message': 'Kapten tidak dapat menghapus diri sendiri.'}, status=400)

    team.members.remove(member)
    updated_members = list(team.members.values('id', 'username'))

    return JsonResponse({
        'status': 'success',
        'removed_member': member.username,
        'members': updated_members
    })

@require_POST
@login_required
def leave_team(request, team_id):
    team = get_object_or_404(Team, id=team_id)

    if team.captain == request.user:
        team.members.remove(request.user)
        team.delete()
        return JsonResponse({'status': 'success'})

    team.members.remove(request.user)
    return JsonResponse({'status': 'success'})

@require_POST
@login_required
def delete_member(request, team_id, member_username):
    team = get_object_or_404(Team, id=team_id, captain=request.user)
    member = get_object_or_404(team.members.all(), username=member_username)

    if member == request.user:
        return JsonResponse({'status': 'error', 'message': 'Kapten tidak dapat menghapus diri sendiri.'}, status=400)

    team.members.remove(member)
    updated_members = list(team.members.values('id', 'username'))

    return JsonResponse({
        'status': 'success',
        'removed_member': member.username,
        'members': updated_members
    })

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

def team_detail_json(request, team_id):
    """Mengambil detail satu tim berdasarkan ID untuk modal detail"""
    team = get_object_or_404(Team, id=team_id)
    
    data = {
        'id': team.id,
        'name': team.name,
        'logo': team.logo.url if team.logo else None,
        'captain': team.captain.username if team.captain else None,
        'members': [member.username for member in team.members.all()],
        'members_count': team.members.count(),
    }
    return JsonResponse(data)
