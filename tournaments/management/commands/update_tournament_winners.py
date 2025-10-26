import sys
import traceback
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from django.db.models import Count, Sum, F, Q
from django.db.models.functions import Coalesce
from tournaments.models import Tournament, Match
from teams.models import Team

class Command(BaseCommand):
    help = 'Checks for tournaments that have ended and assigns a winner based on the ORM leaderboard.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        tournaments_to_check = Tournament.objects.filter(
            end_date__lt=today, 
            winner__isnull=True
        )

        if not tournaments_to_check.exists():
            self.stdout.write(self.style.SUCCESS('No finished tournaments found that need a winner assigned.'))
            return

        self.stdout.write(f'Found {tournaments_to_check.count()} tournaments to process...')
        updated_count = 0

        home_win = Q(home_score__gt=F('away_score'))
        home_draw = Q(home_score=F('away_score'))
        home_loss = Q(home_score__lt=F('away_score'))
        
        away_win = Q(away_score__gt=F('home_score'))
        away_draw = Q(away_score=F('home_score'))
        away_loss = Q(away_score__lt=F('home_score'))

        for tournament in tournaments_to_check:
            self.stdout.write(f'Processing "{tournament.name}" (ID: {tournament.pk})...')
            
            try:
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
                )

                top_team = leaderboard_queryset.first() 

                if top_team:
                    if top_team.played > 0:
                        tournament.winner = top_team
                        tournament.save(update_fields=['winner']) 
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Successfully set winner for "{tournament.name}" to "{top_team.name}".'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Skipping "{tournament.name}": No matches were played, no winner assigned.'))
                else:
                    self.stdout.write(self.style.WARNING(f'Skipping "{tournament.name}": No participants found.'))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error processing tournament {tournament.pk} ({tournament.name}): {e}'))
                traceback.print_exc(file=sys.stderr)

        self.stdout.write(self.style.SUCCESS(f'Finished processing. Updated {updated_count} tournament winners.'))