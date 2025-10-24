from django.contrib import admin
from .models import Thread, Post

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ['title', 'tournament', 'author', 'created_at', 'is_deleted']
    list_filter = ['tournament', 'created_at', 'is_deleted']
    search_fields = ['title', 'author__username']
    actions = ['hard_delete_threads']

    def hard_delete_threads(self, request, queryset):
        """Hard delete selected threads (admin only)"""
        count = queryset.count()
        for thread in queryset:
            thread.delete()  
        self.message_user(request, f'{count} threads permanently deleted.')
    hard_delete_threads.short_description = "Permanently delete selected threads"

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'thread', 'author', 'created_at', 'is_edited', 'is_deleted']
    list_filter = ['thread__tournament', 'created_at', 'is_deleted']
    search_fields = ['body', 'author__username']
    actions = ['hard_delete_posts']

    def hard_delete_posts(self, request, queryset):
        """Hard delete selected posts (admin only)"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} posts permanently deleted.')
    hard_delete_posts.short_description = "Permanently delete selected posts"