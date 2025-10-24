from django.contrib import admin
from .models import Team

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'captain', 'get_members_count')
    list_filter = ('captain',)
    search_fields = ('name', 'captain__username')
    filter_horizontal = ('members',)
    
    fieldsets = (
        ('Team Information', {
            'fields': ('name', 'logo', 'captain')
        }),
        ('Members', {
            'fields': ('members',)
        }),
    )
    
    def get_members_count(self, obj):
        return obj.members.count()
    get_members_count.short_description = 'Members'
    
    # Custom actions
    actions = ['delete_selected_teams', 'clear_all_members']
    
    def delete_selected_teams(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} team(s) deleted successfully.')
    delete_selected_teams.short_description = 'Delete selected teams'
    
    def clear_all_members(self, request, queryset):
        for team in queryset:
            team.members.clear()
            if team.captain:
                team.members.add(team.captain)  # Keep captain as member
        self.message_user(request, f'Cleared members from {queryset.count()} team(s).')
    clear_all_members.short_description = 'Clear all members (keep captain)'

    def change_captain(self, request, queryset):
        for team in queryset:
            if team.members.exists():
                new_captain = team.members.exclude(id=team.captain.id).first()
                if new_captain:
                    team.captain = new_captain
                    team.save()
        self.message_user(request, f'Changed captain for {queryset.count()} team(s).')