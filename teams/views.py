import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError
from .models import Team

# --- Helper Function ---
def is_json_request(request):
    return 'application/json' in request.headers.get('Content-Type', '')

# --- VIEW WEB ---
def show_main_teams(request):
    teams = Team.objects.all()
    user = request.user if request.user.is_authenticated else None
    return render(request, 'teams.html', {'teams': teams, 'user': user})

@csrf_exempt
def search_teams(request):
    query = request.GET.get('q', '').strip()
    mode = request.GET.get('mode', 'join')
    page = request.GET.get('page', 1)

    teams = Team.objects.all().annotate(members_count=Count('members'))

    if request.user.is_authenticated:
        if mode == 'join':
            teams = teams.exclude(members=request.user)
        elif mode == 'meet':
            teams = teams.filter(members=request.user)
        elif mode == 'manage':
            if not request.user.is_superuser:
                teams = teams.filter(captain=request.user)
    else:
        if mode != 'join':
            return JsonResponse({'status': 'error', 'message': 'Login diperlukan.'}, status=401)

    if query:
        teams = teams.filter(
            Q(name__icontains=query) | Q(captain__username__icontains=query)
        )

    paginator = Paginator(teams, 5)
    try:
        page_obj = paginator.get_page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    results = [
        {
            'id': team.id,
            'name': team.name,
            'logo': team.logo if team.logo else None,
            'captain': team.captain.username if team.captain else None,
            'members_count': team.members_count,
        }
        for team in page_obj
    ]

    return JsonResponse({
        'status': 'success',
        'results': results,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })

# --- ACTION API (CREATE) ---
@csrf_exempt
@require_POST
def create_team(request):
    if not request.user.is_authenticated:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Login dulu.'}, status=401)
        return redirect('main:login')

    name = None
    logo = ''

    try:
        data = json.loads(request.body)
        name = data.get('name')
        logo = data.get('logo', '')
    except json.JSONDecodeError:
        name = request.POST.get('name')
        logo = request.POST.get('logo', '')

    if not name:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Nama wajib diisi.'}, status=400)
        messages.error(request, "Nama tim wajib diisi!")
        return redirect('teams:show_main_teams')

    try:
        new_team = Team.objects.create(name=name, logo=logo, captain=request.user)
        new_team.members.add(request.user)
        new_team.save()

        if is_json_request(request):
            return JsonResponse({'status': 'success', 'message': 'Tim berhasil dibuat!', 'team_id': new_team.id}, status=201)
        
        messages.success(request, "Tim berhasil dibuat!")
        return redirect('teams:show_main_teams')

    except IntegrityError:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Nama tim sudah dipakai!'}, status=400)
        messages.error(request, "Nama tim sudah dipakai!")
        return redirect('teams:show_main_teams')
    except Exception as e:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': f'Server Error: {str(e)}'}, status=500)
        messages.error(request, "Terjadi kesalahan server.")
        return redirect('teams:show_main_teams')

# --- OTHER ACTIONS (JOIN, EDIT, DELETE, LEAVE, KICK) ---

@csrf_exempt
@require_POST
def join_team(request, team_id):
    if not request.user.is_authenticated:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Login dulu.'}, status=401)
        return redirect('main:login')

    team = get_object_or_404(Team, id=team_id)

    if request.user in team.members.all():
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Sudah join.'}, status=400)
        messages.warning(request, "Anda sudah bergabung.")
        return redirect('teams:show_main_teams')

    team.members.add(request.user)

    if is_json_request(request):
        return JsonResponse({'status': 'success', 'message': 'Berhasil join!'})
    
    messages.success(request, "Berhasil bergabung!")
    return redirect('teams:show_main_teams')

@csrf_exempt
@require_POST
def edit_team(request, team_id):
    if not request.user.is_authenticated:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Login dulu.'}, status=401)
        return redirect('main:login')

    team = get_object_or_404(Team, id=team_id)
    
    if team.captain != request.user and not request.user.is_superuser:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Bukan kapten.'}, status=403)
        return redirect('teams:show_main_teams')

    name = None
    logo = None

    try:
        data = json.loads(request.body)
        name = data.get('name')
        logo = data.get('logo')
    except json.JSONDecodeError:
        name = request.POST.get('name')
        logo = request.POST.get('logo')
    
    if name:
        team.name = name
    if logo:
        team.logo = logo
    
    try:
        team.save()
        if is_json_request(request):
            return JsonResponse({'status': 'success', 'message': 'Tim diupdate!'})
        messages.success(request, "Tim berhasil diupdate!")
        return redirect('teams:show_main_teams')
    except IntegrityError:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Nama tim sudah dipakai!'}, status=400)
        messages.error(request, "Nama tim sudah dipakai!")
        return redirect('teams:show_main_teams')

@csrf_exempt
@require_POST
def delete_team(request, team_id):
    if not request.user.is_authenticated:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Login dulu.'}, status=401)
        return redirect('main:login')

    team = get_object_or_404(Team, id=team_id)
    
    if team.captain != request.user and not request.user.is_superuser:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Bukan kapten.'}, status=403)
        return redirect('teams:show_main_teams')

    team.delete()

    if is_json_request(request):
        return JsonResponse({'status': 'success', 'message': 'Tim dihapus.'})
    
    messages.success(request, "Tim berhasil dihapus!")
    return redirect('teams:show_main_teams')

@csrf_exempt
@require_POST
def delete_member(request, team_id, member_username):
    if not request.user.is_authenticated:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Login dulu.'}, status=401)
        return redirect('main:login')

    team = get_object_or_404(Team, id=team_id)
    
    if team.captain != request.user and not request.user.is_superuser:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Bukan kapten.'}, status=403)
        return redirect('teams:show_main_teams')
    
    member = get_object_or_404(User, username=member_username)

    if member == request.user:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Jangan kick diri sendiri.'}, status=400)
        return redirect('teams:show_main_teams')

    if member in team.members.all():
        team.members.remove(member)
        if is_json_request(request):
            return JsonResponse({'status': 'success', 'message': f'{member_username} di-kick.'})
        messages.success(request, f"{member_username} berhasil dikeluarkan.")
    else:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Member tidak ditemukan.'}, status=404)
    
    return redirect('teams:show_main_teams')

@csrf_exempt
@require_POST
def leave_team(request, team_id):
    if not request.user.is_authenticated:
        if is_json_request(request):
            return JsonResponse({'status': 'error', 'message': 'Login dulu.'}, status=401)
        return redirect('main:login')

    team = get_object_or_404(Team, id=team_id)

    if team.captain == request.user:
        team.delete()
        if is_json_request(request):
            return JsonResponse({'status': 'success', 'message': 'Tim dibubarkan.'})
        messages.info(request, "Tim dibubarkan karena kapten keluar.")
        return redirect('teams:show_main_teams')

    if request.user in team.members.all():
        team.members.remove(request.user)
        if is_json_request(request):
            return JsonResponse({'status': 'success', 'message': 'Berhasil keluar.'})
        messages.success(request, "Berhasil keluar dari tim.")
        return redirect('teams:show_main_teams')
    
    if is_json_request(request):
        return JsonResponse({'status': 'error', 'message': 'Bukan anggota.'}, status=400)
    return redirect('teams:show_main_teams')

def team_detail_json(request, team_id):
    try:
        team = Team.objects.get(id=team_id)
        data = {
            'id': team.id,
            'name': team.name,
            'logo': team.logo if team.logo else "",
            'captain': team.captain.username if team.captain else "Unknown",
            'members': [member.username for member in team.members.all()],
            'members_count': team.members.count(),
        }
        return JsonResponse(data)
    except Team.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Tim tidak ditemukan'}, status=404)

# --- API FLUTTER UTAMA ---
@csrf_exempt
def team_flutter_api(request):
    if request.method == 'GET':
        teams = Team.objects.all()
        data = []
        for team in teams:
            data.append({
                'id': team.id,
                'name': team.name,
                'logo': team.logo if team.logo else "",
                'captain': team.captain.username if team.captain else "Unknown",
                'members_count': team.members.count(),
                'members': [member.username for member in team.members.all()]
            })
        return JsonResponse({'status': 'success', 'data': data}, safe=False)

    elif request.method == 'POST':
        return create_team(request) 

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)