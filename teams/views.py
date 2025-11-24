from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage
from django.views.decorators.csrf import csrf_exempt
from .models import Team
import json

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
            'logo': team.logo if team.logo else None,
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

@require_POST
@login_required
def create_team(request):
    name = request.POST.get('name')
    logo = request.POST.get('logo')

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
    logo = request.POST.get('logo')

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

# Hapus fungsi ini karena duplikasi dan tidak terdaftar di urls.py
# @require_POST
# @login_required
# def delete_member(request, team_id, member_id):
#     ...

@require_POST
@login_required
def delete_member(request, team_id, member_username):
    # Modifikasi: Jika superuser, bisa delete dari semua team tanpa harus captain
    if request.user.is_superuser:
        team = get_object_or_404(Team, id=team_id)
    else:
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

def show_json(request):
    teams = Team.objects.all()
    data = []
    for team in teams:
        data.append({
            'id': team.id,
            'name': team.name,
            'logo': team.logo if team.logo else None,
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
        'logo': team.logo if team.logo else None,
        'captain': team.captain.username if team.captain else None,
        'members': [member.username for member in team.members.all()],
        'members_count': team.members.count(),
    }
    return JsonResponse(data)

@csrf_exempt
def team_flutter_api(request):
    """
    API Endpoint khusus untuk Flutter/External Apps.
    Method GET: Mengembalikan list team.
    Method POST: Membuat team baru.
    """
    
    # --- HANDLE GET REQUEST (READ DATA) ---
    if request.method == 'GET':
        teams = Team.objects.all()
        
        # Kita format datanya menjadi list of dictionaries
        data = []
        for team in teams:
            data.append({
                'id': team.id,
                'name': team.name,
                'logo': team.logo if team.logo else "", # Handle null/None
                'captain': team.captain.username if team.captain else "No Captain",
                'members_count': team.members.count(),
                # Kirim list member username juga jika perlu
                'members': [member.username for member in team.members.all()]
            })
            
        return JsonResponse({
            'status': 'success',
            'data': data
        }, safe=False)

    # --- HANDLE POST REQUEST (CREATE DATA) ---
    elif request.method == 'POST':
        try:
            # 1. Baca data JSON dari body request (karena Flutter kirim JSON)
            data = json.loads(request.body)
            
            # 2. Validasi input
            name = data.get('name')
            logo = data.get('logo', '') # Default string kosong jika tidak ada
            
            if not name:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Nama tim harus diisi!'
                }, status=400)

            # 3. Cek User (PENTING: Flutter harus handle login cookie/token)
            if not request.user.is_authenticated:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'User belum login.'
                }, status=401)

            # 4. Buat Team
            new_team = Team.objects.create(
                name=name,
                logo=logo,
                captain=request.user
            )
            
            # Tambahkan pembuat sebagai member
            new_team.members.add(request.user)
            new_team.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Tim berhasil dibuat via Flutter!',
                'team_id': new_team.id,
                'team_name': new_team.name
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # --- METHOD NOT ALLOWED ---
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
