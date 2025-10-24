from django.contrib import admin
from .models import Team

# Register your models here.
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'captain', 'member_count')
    list_filter = ('captain',)
    search_fields = ('name', 'captain__username')
    filter_horizontal = ('members',)
    ordering = ('name',)

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Total Members'
