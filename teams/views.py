from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Team

@login_required(login_url='/login')
def show_teams(request):
    teams = Team.objects.all()

    context = {
        'teams': teams,
        'user': request.user,
    }
    
    return render(request, 'teams.html', context)

def create_teams(request):
    return render(request, 'create_teams.html')

def join_teams(request):
    return render(request, 'join_teams.html')

def team_details(request, team_id):
    return render(request, 'team_details.html', {'team_id': team_id})

def edit_team(request, team_id):
    return render(request, 'edit_team.html', {'team_id': team_id})

def delete_team(request, team_id):
    return JsonResponse({'status': 'success'})

def leave_team(request, team_id):
    return JsonResponse({'status': 'success'})

def manage_team_members(request, team_id):
    return render(request, 'manage_team_members.html', {'team_id': team_id})

def manage_team_tournaments(request, team_id):
    return render(request, 'manage_team_tournaments.html', {'team_id': team_id})


