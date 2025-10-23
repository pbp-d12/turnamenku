from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Team

def show_main_teams(request):
    user = request.user 
    return render(request, 'teams.html', {'user': user})

def create_teams(request): #skip dlu lah
    return render(request, 'create_teams.html')

def join_teams(request): 
    teams = Team.objects.all()
    return render(request, 'join_teams.html', {'teams': teams})

def team_details(request, team_id):
    return render(request, 'team_details.html', {'team_id': team_id})

def meet_teams(request):
    teams = Team.objects.all().filter(member=request.user)
    return render(request, 'meet_teams.html', {'teams': teams})

def edit_team(request, team_id):    
    return JsonResponse({'status': 'success'})

def delete_team(request, team_id):
    return JsonResponse({'status': 'success'})

def delete_member(request, team_id, member_id):
    return JsonResponse({'status': 'success'})

def leave_team(request, team_id):
    return JsonResponse({'status': 'success'})

def manage_team(request):
    teams = Team.objects.filter(captain=request.user)
    return render(request, 'manage_team.html', {'teams': teams})

def manage_team_members(request, team_id):
    return render(request, 'manage_team_members.html', {'team_id': team_id})

def manage_team_tournaments(request, team_id):
    return render(request, 'manage_team_tournaments.html', {'team_id': team_id})

def search_teams(request):
    query = request.GET.get('q', '')
    return render(request, 'search_teams.html', {'query': query})

def show_json(request):
    team_list = Team.objects.all()

    data = [
        {
            'name': team.name,
            'logo' : team.logo.url if team.logo else None,
            'captain': team.captain.username if team.captain else None,
            'members': [member.username for member in team.members.all()],
        } 
        for team in team_list
        ]

    return JsonResponse(data, safe=False)


