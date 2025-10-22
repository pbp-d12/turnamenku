from django.contrib import admin
from .models import Thread, Post

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ['title', 'tournament', 'author', 'created_at']
    list_filter = ['tournament', 'created_at']
    search_fields = ['title', 'author__username']
    date_hierarchy = 'created_at'

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['thread', 'author', 'created_at', 'short_body']
    list_filter = ['created_at', 'thread__tournament']
    search_fields = ['body', 'author__username', 'thread__title']
    date_hierarchy = 'created_at'
    
    def short_body(self, obj):
        return obj.body[:50] + "..." if len(obj.body) > 50 else obj.body
    short_body.short_description = 'Body Preview'