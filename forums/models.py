from django.db import models
from django.conf import settings 
from tournaments.models import Tournament 

class Thread(models.Model):
    tournament = models.ForeignKey(Tournament, related_name='threads', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='forum_threads', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Track last update
    is_deleted = models.BooleanField(default=False)  # Soft delete

    def __str__(self):
        return self.title

    @property
    def initial_post(self):
        return self.posts.order_by('created_at').first()

    @property
    def reply_count(self):
        return max(0, self.posts.count() - 1)

class Post(models.Model):
    thread = models.ForeignKey(Thread, related_name='posts', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='forum_posts', on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Track last update
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE, 
        related_name='replies'
    )
    image = models.ImageField(
        upload_to='forum_images/', 
        null=True, 
        blank=True
    )
    is_deleted = models.BooleanField(default=False)  # Soft delete
    
    class Meta:
        ordering = ['created_at'] 

    def __str__(self):
        return f"Post by {self.author.username} in '{self.thread.title}' ({self.pk})"
    
    @property
    def is_edited(self):
        return self.updated_at > self.created_at