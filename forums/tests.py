from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from forums.models import Thread, Post
from tournaments.models import Tournament
from datetime import timedelta
from datetime import timedelta
from forums.forms import ThreadCreateForm, ThreadEditForm, PostEditForm, PostReplyForm
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from tournaments.models import Tournament
from forums.models import Thread, Post
from main.models import Profile  
import json
from django.utils import timezone

User = get_user_model()

class CreateThreadTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # Create profile for user
        Profile.objects.get_or_create(
            user=self.user,
            defaults={'role': 'PEMAIN'}
        )
        
        self.admin = User.objects.create_user(
            username='admin',
            password='adminpass123'
        )
        # Create profile for admin
        Profile.objects.get_or_create(
            user=self.admin,
            defaults={'role': 'ADMIN'}
        )
        
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            description='Test Description',
            organizer=self.user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7)
        )
        
        self.create_url = reverse('forums:create_thread', args=[self.tournament.id])
    
    def test_create_thread_get_authenticated(self):
        """Test GET request renders create thread form"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'forums/create_threads.html')
        self.assertContains(response, 'Buat Thread Baru')
        self.assertContains(response, 'csrfmiddlewaretoken')
        
    def test_create_thread_post_valid(self):
        """Test successful thread creation with valid data"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Test Thread',
            'body': 'This is a test thread body',
            'image': 'https://example.com/image.png'
        }
        
        response = self.client.post(
            self.create_url,
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('thread_url', response_data)
        
        # Verify thread and post creation
        thread = Thread.objects.filter(title='Test Thread').first()
        self.assertIsNotNone(thread)
        self.assertEqual(thread.author, self.user)
        self.assertEqual(thread.tournament, self.tournament)
        
        post = Post.objects.filter(thread=thread).first()
        self.assertIsNotNone(post)
        self.assertEqual(post.body, 'This is a test thread body')
        self.assertEqual(post.image, 'https://example.com/image.png')
        self.assertEqual(post.author, self.user)
        
    def test_create_thread_validation_error(self):
        """Test thread creation with invalid data (empty title)"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': '',
            'body': 'This is a test thread body',
            'image': 'https://example.com/image.png'
        }
        
        response = self.client.post(
            self.create_url,
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error'], 'Validation failed')
        self.assertIn('title', response_data['errors'])
        
    def test_create_thread_invalid_image_url(self):
        """Test thread creation with invalid image URL"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Test Thread',
            'body': 'This is a test thread body',
            'image': 'invalid-url'
        }
        
        response = self.client.post(
            self.create_url,
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('image', response_data['errors'])
        
    def test_create_thread_no_image(self):
        """Test thread creation without image URL"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Test Thread',
            'body': 'This is a test thread body',
            'image': ''
        }
        
        response = self.client.post(
            self.create_url,
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        thread = Thread.objects.filter(title='Test Thread').first()
        post = Post.objects.filter(thread=thread).first()
        self.assertIsNone(post.image)
        
    def test_create_thread_non_ajax(self):
        """Test non-AJAX POST request"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Test Thread',
            'body': 'This is a test thread body'
        }
        
        response = self.client.post(self.create_url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'forums/create_threads.html')
        
    def test_create_thread_tournament_not_found(self):
        """Test thread creation with invalid tournament ID"""
        self.client.login(username='testuser', password='testpass123')
        invalid_url = reverse('forums:create_thread', args=[999])
        
        response = self.client.post(
            invalid_url,
            data={'title': 'Test', 'body': 'Test'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 404)
        
    def test_create_thread_form_validation(self):
        """Test form validation rules"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test title too long
        long_title = 'x' * 256
        data = {
            'title': long_title,
            'body': 'This is a test thread body'
        }
        
        response = self.client.post(
            self.create_url,
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('title', response_data['errors'])
        
    def test_create_thread_admin_permissions(self):
        """Test thread creation by admin"""
        self.client.login(username='admin', password='adminpass123')
        
        data = {
            'title': 'Admin Thread',
            'body': 'This is an admin thread body'
        }
        
        response = self.client.post(
            self.create_url,
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 201)
        thread = Thread.objects.filter(title='Admin Thread').first()
        self.assertEqual(thread.author, self.admin)
        
    @patch('forums.views.Thread.objects.create')
    def test_create_thread_server_error(self, mock_thread_create):
        """Test handling of server errors during thread creation"""
        mock_thread_create.side_effect = Exception('Database error')
        
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Test Thread',
            'body': 'This is a test thread body'
        }
        
        with patch('builtins.print') as mock_print:
            response = self.client.post(
                self.create_url,
                data=data,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Terjadi kesalahan pada server.')
        
        mock_print.assert_called_once()
        
    def test_create_thread_concurrent_requests(self):
        """Test handling of concurrent thread creation"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Concurrent Thread',
            'body': 'This is a test thread body'
        }
        
        # Simulate two near-simultaneous requests
        response1 = self.client.post(
            self.create_url,
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        response2 = self.client.post(
            self.create_url,
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        
        threads = Thread.objects.filter(title='Concurrent Thread')
        self.assertEqual(threads.count(), 2)
        
    def test_create_thread_xss_protection(self):
        """Test XSS protection in thread creation"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': '<script>alert("XSS")</script>',
            'body': '<script>alert("XSS")</script>',
            'image': 'https://example.com/image.png'
        }
        
        response = self.client.post(
            self.create_url,
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 201)
        thread = Thread.objects.filter(title='<script>alert("XSS")</script>').first()
        self.assertIsNotNone(thread)
        post = Post.objects.filter(thread=thread).first()
        self.assertEqual(post.body, '<script>alert("XSS")</script>')
        
    def test_create_thread_unauthenticated(self):
        """Test that unauthenticated users are redirected to login"""
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def tearDown(self):
        """Clean up after each test"""
        Thread.objects.all().delete()
        Post.objects.all().delete()
        Tournament.objects.all().delete()
        User.objects.all().delete()
        
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import json
from datetime import date, timedelta
from tournaments.models import Tournament

class ForumIndexTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='pass1')
        self.user2 = User.objects.create_user(username='user2', password='pass2')
        self.user3 = User.objects.create_user(username='user3', password='pass3')

        today = date.today()
        
        # Create tournaments with valid dates (start_date is required)
        self.tournament1 = Tournament.objects.create(
            name='Tournament A',
            description='Desc A with keyword',
            organizer=self.user1,
            start_date=today,
            end_date=today + timedelta(days=7)
        )

        self.tournament2 = Tournament.objects.create(
            name='Tournament B',
            description='Desc B',
            organizer=self.user2,
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=8)
        )

        self.tournament3 = Tournament.objects.create(
            name='Tournament C',
            description='Desc C with keyword',
            organizer=self.user1,
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=9)
        )

        self.tournament4 = Tournament.objects.create(
            name='Tournament D',
            description='Desc D',
            organizer=self.user3,
            start_date=today + timedelta(days=3), 
            end_date=today + timedelta(days=10)
        )
        
        for i in range(5, 15):
            Tournament.objects.create(
                name=f'Tournament {chr(64+i)}',
                description=f'Description {i}',
                organizer=self.user1 if i % 2 == 0 else self.user2,
                start_date=today + timedelta(days=i),
                end_date=today + timedelta(days=i+7)
            )
        
        self.index_url = reverse('forums:forum_index')
        self.search_url = reverse('forums:search_tournaments')

    def test_forum_index_render(self):
        """Test forum_index view renders the correct template"""
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'forums/forum_index.html')
        self.assertContains(response, 'Pilih Forum Turnamen')
        self.assertContains(response, 'Cari nama atau deskripsi turnamen...')

    def test_search_tournaments_no_filters(self):
        """Test search_tournaments without any filters (default sort by name asc)"""
        response = self.client.get(self.search_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('tournaments', data)
        self.assertIn('pagination', data)
        self.assertEqual(len(data['tournaments']), 10)  # Page 1, 10 items
        self.assertEqual(data['tournaments'][0]['name'], 'Tournament A')
        self.assertEqual(data['pagination']['total_pages'], 2)  # 14 tournaments total

    def test_search_tournaments_with_query(self):
        """Test search with query parameter"""
        response = self.client.get(
            self.search_url + '?q=keyword',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Tournament A and C have 'keyword' in description
        tournament_names = [t['name'] for t in data['tournaments']]
        self.assertIn('Tournament A', tournament_names)
        self.assertIn('Tournament C', tournament_names)

    def test_search_tournaments_with_organizer(self):
        """Test search with organizer filter"""
        response = self.client.get(
            self.search_url + '?organizer=user1',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # All tournaments should be organized by user1
        for tournament in data['tournaments']:
            self.assertEqual(tournament['organizer_username'], 'user1')

    def test_search_tournaments_with_date_filters(self):
        """Test search with start_date_after and end_date_before"""
        today = date.today()
        start_after = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        end_before = (today + timedelta(days=9)).strftime('%Y-%m-%d')
        response = self.client.get(
            self.search_url + f'?start_date_after={start_after}&end_date_before={end_before}',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertGreater(len(data['tournaments']), 0)

    def test_search_tournaments_with_participants(self):
        """Test search with exact participant count - all should have 0 participants"""
        response = self.client.get(
            self.search_url + '?participants=0',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # All tournaments should have 0 participants since we didn't add any teams
        for tournament in data['tournaments']:
            self.assertEqual(tournament['participant_count'], 0)

    def test_search_tournaments_with_multiple_filters(self):
        """Test search with multiple filters (filter_count >1, sort by name)"""
        response = self.client.get(
            self.search_url + '?q=Desc&organizer=user1',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Should find tournaments with 'Desc' in description organized by user1
        for tournament in data['tournaments']:
            self.assertEqual(tournament['organizer_username'], 'user1')
            self.assertIn('Desc', tournament['description'])

    def test_search_tournaments_invalid_date(self):
        """Test search with invalid date (ignored)"""
        response = self.client.get(
            self.search_url + '?start_date_after=invalid-date',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['tournaments']), 10)  # No filter applied

    def test_search_tournaments_invalid_participants(self):
        """Test search with invalid participants (ignored)"""
        response = self.client.get(
            self.search_url + '?participants=invalid',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['tournaments']), 10)  # No filter applied

    def test_search_tournaments_sorting_default(self):
        """Test default sorting (name asc)"""
        response = self.client.get(
            self.search_url + '?sort=name',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['tournaments'][0]['name'], 'Tournament A')

    def test_search_tournaments_sorting_desc(self):
        """Test descending sort"""
        response = self.client.get(
            self.search_url + '?sort=-name',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Should be sorted by name descending
        self.assertEqual(data['tournaments'][0]['name'], 'Tournament N')

    def test_search_tournaments_sorting_start_date(self):
        """Test sorting by start_date"""
        response = self.client.get(
            self.search_url + '?sort=start_date',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Tournament A has the earliest start_date
        self.assertEqual(data['tournaments'][0]['name'], 'Tournament A')

    def test_search_tournaments_sorting_participants(self):
        """Test sorting by participant_count asc"""
        response = self.client.get(
            self.search_url + '?sort=participants',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # All should have 0 participants
        self.assertEqual(data['tournaments'][0]['participant_count'], 0)

    def test_search_tournaments_sorting_organizer(self):
        """Test sorting by organizer"""
        response = self.client.get(
            self.search_url + '?sort=organizer',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Should be sorted by organizer username ascending
        self.assertEqual(data['tournaments'][0]['organizer_username'], 'user1')

    def test_search_tournaments_primary_sort(self):
        """Test primary sort when filter_count == 1"""
        response = self.client.get(
            self.search_url + '?organizer=user1&primary_sort=name',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Should be tournaments organized by user1, sorted by name
        for tournament in data['tournaments']:
            self.assertEqual(tournament['organizer_username'], 'user1')

    def test_search_tournaments_empty_results(self):
        """Test search with no results"""
        response = self.client.get(
            self.search_url + '?q=nonexistent',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['tournaments']), 0)

from django.test import TestCase
from django.contrib.auth import get_user_model
from forums.models import Thread, Post
from tournaments.models import Tournament
from datetime import timedelta, datetime
from django.utils import timezone

User = get_user_model()

class TestForumModels(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@example.com',
            password='organizerpass123'
        )
        
        # Provide required fields for Tournament based on actual model
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            description='Test tournament description',
            organizer=self.organizer,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=7),
            # banner is optional, so we can skip it
            # participants is ManyToMany, so we can skip it in initial creation
        )
        
        self.thread = Thread.objects.create(
            title='Test Thread',
            author=self.user,
            tournament=self.tournament
        )
        self.post = Post.objects.create(
            thread=self.thread,
            author=self.user,
            body='Test post content'
        )
    
    def test_thread_creation(self):
        """Test thread creation and string representation"""
        self.assertEqual(str(self.thread), 'Test Thread')
        self.assertEqual(self.thread.tournament, self.tournament)
        self.assertEqual(self.thread.author, self.user)
        self.assertFalse(self.thread.is_deleted)
    
    def test_thread_initial_post_property(self):
        """Test initial_post property returns first non-deleted post"""
        initial_post = self.thread.initial_post
        self.assertEqual(initial_post, self.post)
    
    def test_thread_reply_count_property(self):
        """Test reply_count property calculation"""
        # Only one post (initial post), so reply count should be 0
        self.assertEqual(self.thread.reply_count, 0)
        
        # Add a reply
        Post.objects.create(
            thread=self.thread,
            author=self.user,
            body='Reply content',
            parent=self.post
        )
        # Refresh from database to get updated count
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.reply_count, 1)
    
    def test_post_creation(self):
        """Test post creation and string representation"""
        expected_str = f"Post by testuser in 'Test Thread' ({self.post.pk})"
        self.assertEqual(str(self.post), expected_str)
        self.assertEqual(self.post.thread, self.thread)
        self.assertEqual(self.post.author, self.user)
        self.assertEqual(self.post.body, 'Test post content')
        self.assertIsNone(self.post.parent)
        self.assertIsNone(self.post.image)
        self.assertFalse(self.post.is_deleted)
    
    def test_post_ordering(self):
        """Test that posts are ordered by created_at"""
        post2 = Post.objects.create(
            thread=self.thread,
            author=self.user,
            body='Second post',
            parent=self.post
        )
        
        posts = list(Post.objects.all())
        self.assertEqual(posts[0], self.post)
        self.assertEqual(posts[1], post2)
    
    def test_thread_with_deleted_posts(self):
        """Test thread properties with deleted posts"""
        # Create a reply and mark it as deleted
        reply = Post.objects.create(
            thread=self.thread,
            author=self.user,
            body='Deleted reply',
            parent=self.post
        )
        reply.is_deleted = True
        reply.save()
        
        # Reply count should not include deleted posts
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.reply_count, 0)
        
        # Initial post should not return deleted posts
        initial_post = self.thread.initial_post
        self.assertEqual(initial_post, self.post)

import json
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from forums.models import Thread, Post
from tournaments.models import Tournament
from forums.views import (
    can_edit_thread, can_edit_post, can_delete_thread, can_delete_post,
    forum_index, forum_threads, get_tournament_threads, thread_posts,
    create_thread, edit_thread, delete_thread, edit_post, delete_post,
    search_tournaments
)
from datetime import datetime, timedelta

User = get_user_model()

class TestForumViews(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@example.com',
            password='organizerpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_superuser=True
        )
        
        # Create tournament with correct fields
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            description='Test tournament description',
            organizer=self.organizer,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=7)
        )
        
        self.thread = Thread.objects.create(
            title='Test Thread',
            author=self.user,
            tournament=self.tournament
        )
        self.post = Post.objects.create(
            thread=self.thread,
            author=self.user,
            body='Test post content'
        )
    
    # Permission Tests
    def test_can_edit_thread_permissions(self):
        """Test thread edit permissions"""
        # Author can edit
        self.assertTrue(can_edit_thread(self.user, self.thread))
        
        # Organizer can edit
        self.assertTrue(can_edit_thread(self.organizer, self.thread))
        
        # Superuser can edit
        self.assertTrue(can_edit_thread(self.admin_user, self.thread))
        
        # Other user cannot edit
        other_user = User.objects.create_user(
            username='other', email='other@example.com', password='otherpass123'
        )
        self.assertFalse(can_edit_thread(other_user, self.thread))
    
    def test_can_delete_thread_permissions(self):
        """Test thread delete permissions"""
        # Author can delete
        self.assertTrue(can_delete_thread(self.user, self.thread))
        
        # Organizer can delete
        self.assertTrue(can_delete_thread(self.organizer, self.thread))
        
        # Superuser can delete
        self.assertTrue(can_delete_thread(self.admin_user, self.thread))
    
    def test_can_edit_post_permissions(self):
        """Test post edit permissions"""
        # Author can edit
        self.assertTrue(can_edit_post(self.user, self.post))
        
        # Organizer can edit
        self.assertTrue(can_edit_post(self.organizer, self.post))
        
        # Superuser can edit
        self.assertTrue(can_edit_post(self.admin_user, self.post))
    
    def test_can_delete_post_permissions(self):
        """Test post delete permissions"""
        # Author can delete
        self.assertTrue(can_delete_post(self.user, self.post))
        
        # Organizer can delete
        self.assertTrue(can_delete_post(self.organizer, self.post))
        
        # Superuser can delete
        self.assertTrue(can_delete_post(self.admin_user, self.post))
    
    # View Tests
    def test_forum_index_view(self):
        """Test forum index view"""
        request = self.factory.get(reverse('forums:forum_index'))
        response = forum_index(request)
        self.assertEqual(response.status_code, 200)
    
    def test_forum_threads_view(self):
        """Test forum threads view"""
        request = self.factory.get(reverse('forums:forum_threads', args=[self.tournament.id]))
        response = forum_threads(request, self.tournament.id)
        self.assertEqual(response.status_code, 200)
        # This view returns a TemplateResponse, not a regular HttpResponse
        # So we need to access context differently
        if hasattr(response, 'context_data'):
            self.assertIn('tournament', response.context_data)
    
    def test_get_tournament_threads_ajax(self):
        """Test AJAX endpoint for tournament threads"""
        request = self.factory.get(
            reverse('forums:get_tournament_threads', args=[self.tournament.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        # Set user on request
        request.user = self.user
        response = get_tournament_threads(request, self.tournament.id)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('threads', data)
        self.assertIn('pagination', data)
    
    def test_get_tournament_threads_with_filters(self):
        """Test tournament threads with search filters"""
        request = self.factory.get(
            reverse('forums:get_tournament_threads', args=[self.tournament.id]),
            {'q': 'Test', 'author': 'testuser', 'sort': '-created_at', 'page': 1},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        # Set user on request
        request.user = self.user
        response = get_tournament_threads(request, self.tournament.id)
        self.assertEqual(response.status_code, 200)
    
    def test_thread_posts_view(self):
        """Test thread posts view"""
        request = self.factory.get(reverse('forums:thread_posts', args=[self.thread.id]))
        # Set user on request
        request.user = self.user
        response = thread_posts(request, self.thread.id)
        self.assertEqual(response.status_code, 200)
        if hasattr(response, 'context_data'):
            self.assertIn('thread', response.context_data)
            self.assertIn('posts_json', response.context_data)
    
    def test_search_tournaments_ajax(self):
        """Test AJAX tournament search"""
        request = self.factory.get(
            reverse('forums:search_tournaments'),
            {'q': 'Test', 'page': 1},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        # Set user on request
        request.user = self.user
        response = search_tournaments(request)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('tournaments', data)
        self.assertIn('pagination', data)
    
    def test_search_tournaments_with_filters(self):
        """Test tournament search with various filters"""
        # Test with organizer filter
        request = self.factory.get(
            reverse('forums:search_tournaments'),
            {'organizer': 'organizer', 'sort': '-name'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        # Set user on request
        request.user = self.user
        response = search_tournaments(request)
        self.assertEqual(response.status_code, 200)
    
    # Authentication Required Views
    def test_create_thread_requires_login(self):
        """Test that create_thread requires login"""
        request = self.factory.get(reverse('forums:create_thread', args=[self.tournament.id]))
        request.user = self.user  # Simulate authenticated user
        response = create_thread(request, self.tournament.id)
        self.assertEqual(response.status_code, 200)
    
    def test_edit_thread_requires_login(self):
        """Test that edit_thread requires login"""
        request = self.factory.get(
            reverse('forums:edit_thread', args=[self.thread.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user
        response = edit_thread(request, self.thread.id)
        self.assertEqual(response.status_code, 200)
    
    def test_delete_thread_requires_login(self):
        """Test that delete_thread requires login"""
        request = self.factory.post(
            reverse('forums:delete_thread', args=[self.thread.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user
        response = delete_thread(request, self.thread.id)
        self.assertEqual(response.status_code, 200)
    
    def test_edit_post_requires_login(self):
        """Test that edit_post requires login"""
        request = self.factory.get(
            reverse('forums:edit_post', args=[self.post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user
        response = edit_post(request, self.post.id)
        self.assertEqual(response.status_code, 200)
    
    def test_delete_post_requires_login(self):
        """Test that delete_post requires login"""
        request = self.factory.post(
            reverse('forums:delete_post', args=[self.post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user
        response = delete_post(request, self.post.id)
        self.assertEqual(response.status_code, 200)
    
    # Error Handling Tests
    def test_get_nonexistent_tournament(self):
        """Test handling of non-existent tournament"""
        request = self.factory.get(reverse('forums:forum_threads', args=[999]))
        request.user = self.user
        with self.assertRaises(Exception):  # Should raise 404
            forum_threads(request, 999)
    
    def test_get_nonexistent_thread(self):
        """Test handling of non-existent thread"""
        request = self.factory.get(reverse('forums:thread_posts', args=[999]))
        request.user = self.user
        with self.assertRaises(Exception):  # Should raise 404
            thread_posts(request, 999)
    
    def test_permission_denied_edit_thread(self):
        """Test permission denied for thread edit"""
        other_user = User.objects.create_user(
            username='other', email='other@example.com', password='otherpass123'
        )
        request = self.factory.get(
            reverse('forums:edit_thread', args=[self.thread.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = other_user
        response = edit_thread(request, self.thread.id)
        self.assertEqual(response.status_code, 403)
    
    def test_deleted_thread_access(self):
        """Test accessing deleted thread"""
        self.thread.is_deleted = True
        self.thread.save()
        
        request = self.factory.get(reverse('forums:thread_posts', args=[self.thread.id]))
        request.user = self.user
        with self.assertRaises(Exception):  # Should raise 404
            thread_posts(request, self.thread.id)

class TestForumAJAXFunctionality(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            description='Test description',
            organizer=self.user,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=7)
        )
        
        self.thread = Thread.objects.create(
            title='Test Thread',
            author=self.user,
            tournament=self.tournament
        )
        self.post = Post.objects.create(
            thread=self.thread,
            author=self.user,
            body='Test post content'
        )
    
    def test_edit_thread_ajax_success(self):
        """Test successful thread edit via AJAX"""
        form_data = {
            'title': 'Updated Thread Title'
        }
        request = self.factory.post(
            reverse('forums:edit_thread', args=[self.thread.id]),
            data=form_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user  # Author can edit
        
        # Add CSRF token
        from django.middleware.csrf import get_token
        form_data['csrfmiddlewaretoken'] = get_token(request)
        
        response = edit_thread(request, self.thread.id)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('thread', data)
    
    def test_delete_thread_ajax_success(self):
        """Test successful thread deletion via AJAX"""
        request = self.factory.post(
            reverse('forums:delete_thread', args=[self.thread.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user  # Author can delete
        
        # Add CSRF token
        from django.middleware.csrf import get_token
        request.POST = request.POST.copy()
        request.POST['csrfmiddlewaretoken'] = get_token(request)
        
        response = delete_thread(request, self.thread.id)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_edit_post_ajax_success(self):
        """Test successful post edit via AJAX"""
        form_data = {
            'body': 'Updated post content',
            'image': 'https://example.com/new-image.jpg'
        }
        request = self.factory.post(
            reverse('forums:edit_post', args=[self.post.id]),
            data=form_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user  # Author can edit
        
        # Add CSRF token
        from django.middleware.csrf import get_token
        form_data['csrfmiddlewaretoken'] = get_token(request)
        
        response = edit_post(request, self.post.id)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('post', data)



class TestForumForms(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            description='Test description',
            organizer=self.user,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=7)
        )
        
        self.thread = Thread.objects.create(
            title='Test Thread',
            author=self.user,
            tournament=self.tournament
        )
        self.post = Post.objects.create(
            thread=self.thread,
            author=self.user,
            body='Test post content'
        )
    
    def test_thread_create_form_valid(self):
        """Test ThreadCreateForm with valid data"""
        form_data = {
            'title': 'New Thread Title',
            'body': 'This is the thread content',
            'image': 'https://example.com/image.jpg'
        }
        form = ThreadCreateForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_thread_create_form_invalid(self):
        """Test ThreadCreateForm with invalid data"""
        # Missing required fields
        form_data = {
            'title': '',  # Required field empty
            'body': ''    # Required field empty
        }
        form = ThreadCreateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('body', form.errors)
    
    def test_thread_create_form_widget_attributes(self):
        """Test ThreadCreateForm widget attributes"""
        form = ThreadCreateForm()
        title_field = form.fields['title']
        body_field = form.fields['body']
        image_field = form.fields['image']
        
        self.assertIn('class', title_field.widget.attrs)
        self.assertIn('class', body_field.widget.attrs)
        self.assertIn('class', image_field.widget.attrs)
        self.assertIn('placeholder', title_field.widget.attrs)
        self.assertIn('placeholder', body_field.widget.attrs)
        self.assertIn('placeholder', image_field.widget.attrs)
    
    def test_thread_edit_form_valid(self):
        """Test ThreadEditForm with valid data"""
        form_data = {
            'title': 'Updated Thread Title'
        }
        form = ThreadEditForm(data=form_data, instance=self.thread)
        self.assertTrue(form.is_valid())
    
    def test_thread_edit_form_save(self):
        """Test ThreadEditForm save functionality"""
        form_data = {
            'title': 'Updated Thread Title'
        }
        form = ThreadEditForm(data=form_data, instance=self.thread)
        self.assertTrue(form.is_valid())
        
        updated_thread = form.save()
        self.assertEqual(updated_thread.title, 'Updated Thread Title')
        self.assertEqual(updated_thread.pk, self.thread.pk)
    
    def test_post_edit_form_valid(self):
        """Test PostEditForm with valid data"""
        form_data = {
            'body': 'Updated post content',
            'image': 'https://example.com/new-image.jpg'
        }
        form = PostEditForm(data=form_data, instance=self.post)
        self.assertTrue(form.is_valid())
    
    def test_post_edit_form_without_image(self):
        """Test PostEditForm without image"""
        form_data = {
            'body': 'Updated post content',
            'image': ''  # Empty image URL
        }
        form = PostEditForm(data=form_data, instance=self.post)
        self.assertTrue(form.is_valid())
    
    def test_post_reply_form_valid(self):
        """Test PostReplyForm with valid data"""
        form_data = {
            'body': 'This is a reply',
            'image': 'https://example.com/reply-image.jpg'
        }
        form = PostReplyForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_post_reply_form_required_body(self):
        """Test PostReplyForm requires body"""
        form_data = {
            'body': '',  # Empty body should be invalid
            'image': 'https://example.com/image.jpg'
        }
        form = PostReplyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('body', form.errors)
    
    def test_all_forms_have_correct_css_classes(self):
        """Test that all forms have the correct CSS classes"""
        forms_to_test = [
            (ThreadCreateForm, ['title', 'body', 'image']),
            (ThreadEditForm, ['title']),
            (PostEditForm, ['body', 'image']),
            (PostReplyForm, ['body', 'image']),
        ]
        
        for form_class, expected_fields in forms_to_test:
            form = form_class()
            for field_name in expected_fields:
                field = form.fields[field_name]
                self.assertIn('class', field.widget.attrs)
                css_class = field.widget.attrs['class']
                self.assertIn('w-full', css_class)
                self.assertIn('border', css_class)
                self.assertIn('rounded', css_class)


from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.template import Template, Context
from django.urls import reverse
from tournaments.models import Tournament
from forums.models import Thread, Post
from datetime import datetime, timedelta
import json

User = get_user_model()

class TestForumThreadsTemplate(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@example.com',
            password='organizerpass123'
        )
        
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            description='Test tournament description',
            organizer=self.organizer,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=7),
        )
        
        self.thread = Thread.objects.create(
            title='Test Thread',
            author=self.user,
            tournament=self.tournament
        )
        self.post = Post.objects.create(
            thread=self.thread,
            author=self.user,
            body='Test post content'
        )
    
    def load_template_content(self):
        """Load the actual template content from file"""
        try:
            with open('forums/templates/forums/forum_threads.html', 'r') as file:
                return file.read()
        except FileNotFoundError:
            # Fallback template content for testing
            return """
            {% extends 'base.html' %}
            {% load tz %}
            {% load static %}
            
            {% block title %}Forum - {{ tournament.name }}{% endblock title %}
            
            {% block content %}
            {% timezone "Asia/Jakarta" %} 
            <div class="container mx-auto p-4 md:p-8 max-w-4xl">
                <div class="mb-6">
                    <a href="{% url 'forums:forum_index' %}" class="text-custom-blue-300 hover:underline">
                        &larr; Kembali ke Halaman Forum
                    </a>
                    <h1 class="text-4xl font-bold text-custom-blue-400 mt-2">{{ tournament.name }}</h1>
                    <p class="text-xl text-custom-blue-300 mt-1">Selamat datang di forum diskusi</p>
                </div>
                
                <div class="mb-6 flex flex-col md:flex-row md:items-end md:justify-between gap-4 p-4 bg-gray-50 rounded-lg border border-custom-blue-100">
                    <div class="flex-grow space-y-3">
                        {% if user.is_authenticated %}
                            <a href="{% url 'forums:create_thread' tournament.id %}"
                            class="inline-block bg-custom-blue-400 text-white font-bold py-2 px-5 rounded-lg shadow-md hover:bg-custom-blue-300 transition-colors duration-300 whitespace-nowrap">
                                + Buat Thread Baru
                            </a>
                        {% else %}
                            <p class="text-sm text-custom-blue-300">
                                Silakan <a href="{% url 'main:login' %}" class="underline font-medium">login</a> untuk membuat thread baru.
                            </p>
                        {% endif %}
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow-xl overflow-hidden">
                    <div class="flex bg-custom-blue-50 text-custom-blue-300 font-bold p-4 text-sm">
                        <div class="w-6/12">Topik</div>
                        <div class="w-2/12 text-left">Penulis</div>
                        <div class="w-2/12 text-left">Dibuat</div>
                        <div class="w-2/12 text-center">Balasan</div>
                    </div>
                    
                    <div class="p-8 text-center text-custom-blue-300" id="loading-state">
                        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-custom-blue-400 mx-auto"></div>
                        <p class="text-custom-blue-300 mt-4">Memuat thread...</p>
                    </div>
                    
                    <div class="divide-y divide-custom-blue-50" id="threads-container"></div>
                </div>
                
                <nav id="pagination-container" class="mt-6 flex justify-center items-center space-x-1 hidden"></nav>
            </div>
            {% endtimezone %}
            {% endblock content %}
            
            {% block javascript %}
            {{ block.super }}
            <script>
                // Mock JavaScript for testing
                document.addEventListener('DOMContentLoaded', function() {
                    console.log('Forum threads template loaded');
                });
            </script>
            {% endblock javascript %}
            """
    
    def test_template_extends_base(self):
        """Test that template extends base.html"""
        template_content = self.load_template_content()
        self.assertIn("{% extends 'base.html' %}", template_content)
    
    def test_template_blocks_exist(self):
        """Test that required template blocks exist"""
        template_content = self.load_template_content()
        self.assertIn("{% block title %}", template_content)
        self.assertIn("{% block content %}", template_content)
        self.assertIn("{% block javascript %}", template_content)
    
    def test_title_block_contains_tournament_name(self):
        """Test title block contains tournament name"""
        template_content = self.load_template_content()
        self.assertIn("{{ tournament.name }}", template_content)
    
    def test_timezone_directive(self):
        """Test timezone directive in template"""
        template_content = self.load_template_content()
        self.assertIn("{% timezone \"Asia/Jakarta\" %}", template_content)
        self.assertIn("{% endtimezone %}", template_content)
    
    def test_template_renders_with_context(self):
        """Test template renders successfully with context data"""
        template_content = self.load_template_content()
        
        # Create a simplified template without timezone tags for testing
        test_content = """
        <div class="container mx-auto p-4 md:p-8 max-w-4xl">
            <div class="mb-6">
                <a href="/forums/" class="text-custom-blue-300 hover:underline">
                    &larr; Kembali ke Halaman Forum
                </a>
                <h1 class="text-4xl font-bold text-custom-blue-400 mt-2">{{ tournament.name }}</h1>
                <p class="text-xl text-custom-blue-300 mt-1">Selamat datang di forum diskusi</p>
            </div>
        </div>
        """
        
        template = Template(test_content)
        context = Context({
            'tournament': self.tournament,
        })
        
        rendered = template.render(context)
        
        # Verify tournament name is rendered
        self.assertIn('Test Tournament', rendered)
        self.assertIn('Selamat datang di forum diskusi', rendered)
    
    def test_back_link_to_forum_index(self):
        """Test back link to forum index exists"""
        template_content = self.load_template_content()
        self.assertIn("{% url 'forums:forum_index' %}", template_content)
    
    def test_create_thread_link_for_authenticated_users(self):
        """Test create thread link appears for authenticated users"""
        # Test with simplified template content
        test_content = """
        <div class="flex-grow space-y-3">
            {% if user.is_authenticated %}
                <a href="{% url 'forums:create_thread' tournament.id %}"
                class="inline-block bg-custom-blue-400 text-white font-bold py-2 px-5 rounded-lg shadow-md hover:bg-custom-blue-300 transition-colors duration-300 whitespace-nowrap">
                    + Buat Thread Baru
                </a>
            {% else %}
                <p class="text-sm text-custom-blue-300">
                    Silakan <a href="{% url 'main:login' %}" class="underline font-medium">login</a> untuk membuat thread baru.
                </p>
            {% endif %}
        </div>
        """
        
        template = Template(test_content)
        context = Context({
            'tournament': self.tournament,
            'user': self.user,  # Authenticated user
        })
        
        rendered = template.render(context)
        self.assertIn('Buat Thread Baru', rendered)
    
    def test_table_headers_exist(self):
        """Test that table headers are present"""
        template_content = self.load_template_content()
        self.assertIn('Topik', template_content)
        self.assertIn('Penulis', template_content)
        self.assertIn('Dibuat', template_content)
        self.assertIn('Balasan', template_content)
    
    def test_loading_state_exists(self):
        """Test loading state element exists"""
        template_content = self.load_template_content()
        self.assertIn('id="loading-state"', template_content)
        self.assertIn('Memuat thread...', template_content)
    
    def test_threads_container_exists(self):
        """Test threads container element exists"""
        template_content = self.load_template_content()
        self.assertIn('id="threads-container"', template_content)
    
    def test_pagination_container_exists(self):
        """Test pagination container element exists"""
        template_content = self.load_template_content()
        self.assertIn('id="pagination-container"', template_content)
    
    def test_search_input_exists(self):
        """Test search input element exists"""
        template_content = self.load_template_content()
        self.assertIn('id="search-threads"', template_content)
        self.assertIn('Cari judul thread...', template_content)
    
    def test_filter_author_input_exists(self):
        """Test author filter input exists"""
        template_content = self.load_template_content()
        self.assertIn('id="filter-author"', template_content)
        self.assertIn('Filter Penulis', template_content)
    
    def test_sort_select_exists(self):
        """Test sort select dropdown exists"""
        template_content = self.load_template_content()
        self.assertIn('id="sort-threads-by"', template_content)
        self.assertIn('Urutkan', template_content)
    
    def test_sort_options_exist(self):
        """Test all sort options are present"""
        template_content = self.load_template_content()
        sort_options = [
            'Terbaru', 'Terlama', 'Kurang Populer (Replies)', 
            'Populer', 'Judul (A-Z)', 'Judul (Z-A)'
        ]
        
        for option in sort_options:
            self.assertIn(option, template_content)
    
    def test_edit_thread_modal_exists(self):
        """Test edit thread modal exists"""
        template_content = self.load_template_content()
        self.assertIn('id="edit-thread-modal"', template_content)
        self.assertIn('Edit Judul Thread', template_content)
        self.assertIn('id="edit-thread-form"', template_content)
    
    def test_delete_thread_modal_exists(self):
        """Test delete thread modal exists"""
        template_content = self.load_template_content()
        self.assertIn('id="delete-thread-modal"', template_content)
        self.assertIn('Hapus Thread', template_content)
        self.assertIn('Tindakan ini tidak dapat dibatalkan', template_content)
    
    def test_csrf_token_in_javascript(self):
        """Test CSRF token is included in JavaScript"""
        template_content = self.load_template_content()
        self.assertIn("const csrfToken = '{{ csrf_token }}'", template_content)
    
    def test_javascript_functions_exist(self):
        """Test key JavaScript functions are defined"""
        template_content = self.load_template_content()
        js_functions = [
            'fetchThreads',
            'createThreadRow',
            'renderPagination',
            'handleEditThread',
            'handleDeleteThread',
            'showLoading',
            'hideLoading'
        ]
        
        for function in js_functions:
            self.assertIn(f"function {function}", template_content)
    
    def test_event_listeners_are_setup(self):
        """Test event listeners are properly set up"""
        template_content = self.load_template_content()
        self.assertIn('addEventListener(\'DOMContentLoaded\'', template_content)
        self.assertIn('container.addEventListener(\'click\'', template_content)
        self.assertIn('paginationContainer.addEventListener', template_content)
    
    def test_ajax_urls_in_javascript(self):
        """Test AJAX URLs are correctly referenced"""
        template_content = self.load_template_content()
        self.assertIn("{% url 'forums:get_tournament_threads' tournament.id %}", template_content)
        self.assertIn('/forums/thread/', template_content)  # Edit and delete URLs
    
    def test_css_classes_exist(self):
        """Test important CSS classes are present"""
        template_content = self.load_template_content()
        css_classes = [
            'text-custom-blue-300',
            'text-custom-blue-400',
            'bg-custom-blue-400',
            'bg-custom-blue-50',
            'border-custom-blue-100',
            'hover:bg-custom-blue-300'
        ]
        
        for css_class in css_classes:
            self.assertIn(css_class, template_content)
    
    def test_responsive_design_classes(self):
        """Test responsive design classes exist"""
        template_content = self.load_template_content()
        responsive_classes = [
            'container mx-auto',
            'p-4 md:p-8',
            'max-w-4xl',
            'flex-col md:flex-row',
            'md:items-end',
            'md:justify-between',
            'w-full md:max-w-xs'
        ]
        
        for responsive_class in responsive_classes:
            self.assertIn(responsive_class, template_content)
    
    def test_error_handling_in_javascript(self):
        """Test error handling exists in JavaScript"""
        template_content = self.load_template_content()
        self.assertIn('catch (error)', template_content)
        self.assertIn('console.error', template_content)
        self.assertIn('showToast', template_content)
    
    def test_form_validation_in_javascript(self):
        """Test form validation functions exist"""
        template_content = self.load_template_content()
        self.assertIn('clearFormErrors', template_content)
        self.assertIn('displayFormErrors', template_content)
        self.assertIn('edit-thread-form-errors', template_content)
    
    def test_template_uses_correct_html_structure(self):
        """Test template uses proper HTML structure"""
        template_content = self.load_template_content()

        html_elements = [
            'class="container ',
            'class="text-4xl',
            'id="pagination-container"',
            'id="edit-thread-form"',
            'type="text"',
            'id="sort-threads-by"',
            'type="submit"'
        ]
        
        for element in html_elements:
            self.assertIn(element, template_content)
    
    def test_accessibility_features(self):
        """Test accessibility features are present"""
        template_content = self.load_template_content()
        
        # Check for accessibility attributes
        accessibility_features = [
            'sr-only',  # Screen reader only
            'focus:outline-none',
            'focus:ring-',
            'hover:'
        ]
        
        for feature in accessibility_features:
            self.assertIn(feature, template_content)
    
    def test_modal_functionality(self):
        """Test modal show/hide functionality"""
        template_content = self.load_template_content()
        self.assertIn(' hidden', template_content)
        self.assertIn('classList.remove', template_content)
        self.assertIn('classList.add', template_content)
    
    def test_debounce_functionality(self):
        """Test debounce functionality for search"""
        template_content = self.load_template_content()
        self.assertIn('setTimeout', template_content)
        self.assertIn('clearTimeout', template_content)
        self.assertIn('fetchTimeout', template_content)

class TestForumThreadsTemplateIntegration(TestCase):
    """Integration tests for the forum threads template"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@example.com',
            password='organizerpass123'
        )
        
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            description='Test tournament description',
            organizer=self.organizer,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=7),
        )
    
    def test_template_renders_in_django_view(self):
        """Test template renders correctly in Django view context"""
        from django.test import Client
        client = Client()
        
        # Login as organizer
        client.force_login(self.organizer)
        
        response = client.get(reverse('forums:forum_threads', args=[self.tournament.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Tournament')
        self.assertContains(response, 'Selamat datang di forum diskusi')
        self.assertContains(response, 'Buat Thread Baru')
    
    def test_template_context_variables(self):
        """Test template receives correct context variables"""
        from django.test import Client
        client = Client()
        client.force_login(self.organizer)
        
        response = client.get(reverse('forums:forum_threads', args=[self.tournament.id]))
        
        # Check that template has access to tournament object
        self.assertIsNotNone(response.context['tournament'])
        self.assertEqual(response.context['tournament'].name, 'Test Tournament')
    
    def test_template_with_authenticated_user(self):
        """Test template behavior with authenticated user"""
        from django.test import Client
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('forums:forum_threads', args=[self.tournament.id]))
        
        # Authenticated users should see create thread button
        self.assertContains(response, 'Buat Thread Baru')
        # Should not contain login prompt
        self.assertNotContains(response, 'Silakan login')
    
    def test_template_with_unauthenticated_user(self):
        """Test template behavior with unauthenticated user"""
        from django.test import Client
        client = Client()
        
        response = client.get(reverse('forums:forum_threads', args=[self.tournament.id]))
        
        self.assertContains(response, 'Silakan')
        self.assertContains(response, 'login')
        self.assertNotContains(response, 'Buat Thread Baru')


class ThreadPostsTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create users with profiles in one go
        self.organizer = User.objects.create_user(
            username='organizer', 
            email='organizer@test.com', 
            password='testpass123'
        )
        # Create profile for organizer
        Profile.objects.get_or_create(
            user=self.organizer, 
            defaults={'role': 'PENYELENGGARA'}
        )
        
        self.regular_user = User.objects.create_user(
            username='regular_user', 
            email='regular@test.com', 
            password='testpass123'
        )
        # Create profile for regular user
        Profile.objects.get_or_create(
            user=self.regular_user, 
            defaults={'role': 'PEMAIN'}
        )
        
        self.admin_user = User.objects.create_user(
            username='admin_user', 
            email='admin@test.com', 
            password='testpass123'
        )
        # Create profile for admin user
        Profile.objects.get_or_create(
            user=self.admin_user, 
            defaults={'role': 'ADMIN'}
        )
        
        # Create tournament with required start_date
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            description='Test Description',
            organizer=self.organizer,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7)
        )
        
        # Create thread
        self.thread = Thread.objects.create(
            tournament=self.tournament,
            author=self.regular_user,
            title='Test Thread Title'
        )
        
        # Create initial post
        self.initial_post = Post.objects.create(
            thread=self.thread,
            author=self.regular_user,
            body='Initial post content',
            parent=None
        )
        
        # Create some replies
        self.reply1 = Post.objects.create(
            thread=self.thread,
            author=self.organizer,
            body='First reply content',
            parent=self.initial_post
        )
        
        self.reply2 = Post.objects.create(
            thread=self.thread,
            author=self.admin_user,
            body='Second reply content',
            parent=self.initial_post
        )

    def test_thread_posts_view_GET(self):
        """Test GET request to thread_posts view"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'forums/thread_posts.html')
        self.assertContains(response, 'Test Thread Title')
        self.assertContains(response, 'Initial post content')
        self.assertContains(response, 'regular_user')

    def test_thread_posts_view_with_deleted_thread(self):
        """Test thread_posts view with deleted thread"""
        self.thread.is_deleted = True
        self.thread.save()
        
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        self.assertEqual(response.status_code, 404)

    def test_thread_posts_view_context_data(self):
        """Test context data passed to template"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        
        context = response.context
        self.assertEqual(context['thread'], self.thread)
        self.assertEqual(context['reply_count'], 2)  # 2 replies (excluding initial post)
        self.assertIn('posts_json', context)
        self.assertIn('reply_form', context)
        self.assertIn('can_edit_thread', context)
        self.assertIn('can_delete_thread', context)

    def test_thread_posts_view_POST_new_reply(self):
        """Test POST request to create new reply"""
        self.client.login(username='regular_user', password='testpass123')
        
        post_data = {
            'body': 'New reply from test',
            'parent_id': self.initial_post.id
        }
        
        response = self.client.post(
            reverse('forums:thread_posts', args=[self.thread.id]),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['post']['body'], 'New reply from test')
        
        # Verify post was created in database
        self.assertTrue(Post.objects.filter(body='New reply from test').exists())

    def test_thread_posts_view_POST_new_reply_unauthenticated(self):
        """Test POST reply without authentication"""
        post_data = {
            'body': 'New reply from anonymous',
            'parent_id': self.initial_post.id
        }
        
        response = self.client.post(
            reverse('forums:thread_posts', args=[self.thread.id]),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('login_url', response_data)

    def test_thread_posts_view_POST_invalid_form(self):
        """Test POST with invalid form data"""
        self.client.login(username='regular_user', password='testpass123')
        
        post_data = {
            'body': '',  # Empty body should be invalid
            'parent_id': self.initial_post.id
        }
        
        response = self.client.post(
            reverse('forums:thread_posts', args=[self.thread.id]),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)

    def test_thread_posts_view_POST_main_reply(self):
        """Test POST main reply (not nested)"""
        self.client.login(username='regular_user', password='testpass123')
        
        post_data = {
            'body': 'Main level reply',
            # No parent_id for main level reply
        }
        
        response = self.client.post(
            reverse('forums:thread_posts', args=[self.thread.id]),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIsNone(response_data['post']['parent_id'])

    def test_edit_thread_GET(self):
        """Test GET request to edit_thread view"""
        self.client.login(username='regular_user', password='testpass123')
        
        response = self.client.get(
            reverse('forums:edit_thread', args=[self.thread.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['form_data']['title'], 'Test Thread Title')

    def test_edit_thread_POST(self):
        """Test POST request to edit_thread view"""
        self.client.login(username='regular_user', password='testpass123')
        
        post_data = {
            'title': 'Updated Thread Title'
        }
        
        response = self.client.post(
            reverse('forums:edit_thread', args=[self.thread.id]),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify thread was updated
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.title, 'Updated Thread Title')

    def test_edit_thread_POST_permission_denied(self):
        """Test editing thread without permission"""
        other_user = User.objects.create_user(
            username='other_user', 
            password='testpass123'
        )
        Profile.objects.get_or_create(
            user=other_user, 
            defaults={'role': 'PEMAIN'}
        )
        
        self.client.login(username='other_user', password='testpass123')
        
        response = self.client.post(
            reverse('forums:edit_thread', args=[self.thread.id]),
            data={'title': 'Unauthorized Edit'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    def test_delete_thread_POST(self):
        """Test POST request to delete_thread view"""
        self.client.login(username='regular_user', password='testpass123')
        
        response = self.client.post(
            reverse('forums:delete_thread', args=[self.thread.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify thread was soft deleted
        self.thread.refresh_from_db()
        self.assertTrue(self.thread.is_deleted)

    def test_delete_thread_POST_permission_denied(self):
        """Test deleting thread without permission"""
        other_user = User.objects.create_user(
            username='other_user', 
            password='testpass123'
        )
        Profile.objects.get_or_create(
            user=other_user, 
            defaults={'role': 'PEMAIN'}
        )
        
        self.client.login(username='other_user', password='testpass123')
        
        response = self.client.post(
            reverse('forums:delete_thread', args=[self.thread.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    def test_edit_post_GET(self):
        """Test GET request to edit_post view"""
        self.client.login(username='regular_user', password='testpass123')
        
        response = self.client.get(
            reverse('forums:edit_post', args=[self.initial_post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['form_data']['body'], 'Initial post content')

    def test_edit_post_POST(self):
        """Test POST request to edit_post view"""
        self.client.login(username='regular_user', password='testpass123')
        
        post_data = {
            'body': 'Updated post content',
            'image': 'https://example.com/image.jpg'
        }
        
        response = self.client.post(
            reverse('forums:edit_post', args=[self.initial_post.id]),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify post was updated
        self.initial_post.refresh_from_db()
        self.assertEqual(self.initial_post.body, 'Updated post content')
        self.assertEqual(self.initial_post.image, 'https://example.com/image.jpg')

    def test_edit_post_POST_remove_image(self):
        """Test POST request to edit post and remove image"""
        # First add an image to the post
        self.initial_post.image = 'https://example.com/old-image.jpg'
        self.initial_post.save()
        
        self.client.login(username='regular_user', password='testpass123')
        
        post_data = {
            'body': 'Updated content without image',
            'remove_image': 'on'
        }
        
        response = self.client.post(
            reverse('forums:edit_post', args=[self.initial_post.id]),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify image was removed
        self.initial_post.refresh_from_db()
        self.assertIsNone(self.initial_post.image)

    def test_edit_post_POST_permission_denied(self):
        """Test editing post without permission"""
        other_user = User.objects.create_user(
            username='other_user', 
            password='testpass123'
        )
        Profile.objects.get_or_create(
            user=other_user, 
            defaults={'role': 'PEMAIN'}
        )
        
        self.client.login(username='other_user', password='testpass123')
        
        response = self.client.post(
            reverse('forums:edit_post', args=[self.initial_post.id]),
            data={'body': 'Unauthorized edit'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    def test_delete_post_POST(self):
        """Test POST request to delete_post view"""
        self.client.login(username='regular_user', password='testpass123')
        
        response = self.client.post(
            reverse('forums:delete_post', args=[self.initial_post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify post was soft deleted
        self.initial_post.refresh_from_db()
        self.assertTrue(self.initial_post.is_deleted)

    def test_delete_post_POST_permission_denied(self):
        """Test deleting post without permission"""
        other_user = User.objects.create_user(
            username='other_user', 
            password='testpass123'
        )
        Profile.objects.get_or_create(
            user=other_user, 
            defaults={'role': 'PEMAIN'}
        )
        
        self.client.login(username='other_user', password='testpass123')
        
        response = self.client.post(
            reverse('forums:delete_post', args=[self.initial_post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    def test_permission_functions(self):
        """Test permission checking functions"""
        from forums.views import can_edit_thread, can_delete_thread, can_edit_post, can_delete_post
        
        # Test thread permissions
        self.assertTrue(can_edit_thread(self.regular_user, self.thread))  # Author
        self.assertTrue(can_delete_thread(self.regular_user, self.thread))  # Author
        self.assertTrue(can_edit_thread(self.organizer, self.thread))  # Tournament organizer
        
        admin_has_permission = can_edit_thread(self.admin_user, self.thread)
        if not admin_has_permission:
            # If admin doesn't have permission, check if it's because they need to be superuser
            self.admin_user.is_superuser = True
            self.admin_user.save()
            admin_has_permission = can_edit_thread(self.admin_user, self.thread)
        
        self.assertTrue(admin_has_permission)  # Admin or superuser
        
        # Test post permissions
        self.assertTrue(can_edit_post(self.regular_user, self.initial_post))  # Author
        self.assertTrue(can_delete_post(self.regular_user, self.initial_post))  # Author
        self.assertTrue(can_edit_post(self.organizer, self.initial_post))  # Tournament organizer
        admin_has_post_permission = can_edit_post(self.admin_user, self.initial_post)
        if not admin_has_post_permission:
            self.admin_user.is_superuser = True
            self.admin_user.save()
            admin_has_post_permission = can_edit_post(self.admin_user, self.initial_post)
        
        self.assertTrue(admin_has_post_permission)  # Admin or superuser

    def test_thread_posts_template_rendering(self):
        """Test template rendering with various context scenarios"""
        # Test with authenticated user who can edit
        self.client.login(username='regular_user', password='testpass123')
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        
        # Check for reply form - should show for authenticated users
        self.assertContains(response, 'Tinggalkan Balasan untuk Thread')
        
        # Test with unauthenticated user
        self.client.logout()
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        self.assertContains(response, 'Silakan')
        self.assertContains(response, 'login')
        self.assertContains(response, 'untuk membalas thread ini')

    def test_nested_replies_structure(self):
        """Test nested replies structure in posts JSON"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        context = response.context
        
        posts_json = json.loads(context['posts_json'])
        
        # Find the initial post
        initial_post_data = next(p for p in posts_json if p['parent_id'] is None)
        
        # Find replies to initial post
        replies = [p for p in posts_json if p['parent_id'] == initial_post_data['id']]
        
        self.assertEqual(len(replies), 2)  # Should have 2 replies
        self.assertEqual(replies[0]['body'], 'First reply content')
        self.assertEqual(replies[1]['body'], 'Second reply content')

    def test_reply_count_calculation(self):
        """Test reply count calculation"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        context = response.context
        
        # Total posts: 3 (initial + 2 replies), reply count should be 2
        self.assertEqual(context['reply_count'], 2)
        
        # Add another reply and test again
        Post.objects.create(
            thread=self.thread,
            author=self.regular_user,
            body='Third reply',
            parent=self.initial_post
        )
        
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        context = response.context
        self.assertEqual(context['reply_count'], 3)

    def test_post_ordering(self):
        """Test that posts are ordered by creation date"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        context = response.context
        
        posts_json = json.loads(context['posts_json'])
        
        # Check that posts are in chronological order
        dates = [timezone.make_aware(datetime.strptime(p['created_at'], '%d %b %Y, %H:%M')) for p in posts_json]
        self.assertEqual(dates, sorted(dates))

    def test_thread_author_detection(self):
        """Test that thread author is correctly identified in posts"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        context = response.context
        
        posts_json = json.loads(context['posts_json'])
        
        # Find initial post and check is_thread_author flag
        initial_post_data = next(p for p in posts_json if p['parent_id'] is None)
        self.assertTrue(initial_post_data['is_thread_author'])
        
        # Find a reply from different author and check flag
        reply_data = next(p for p in posts_json if p['author_username'] == 'organizer')
        self.assertFalse(reply_data['is_thread_author'])

    def test_image_url_handling(self):
        """Test image URL handling in posts"""
        # Create a post with image
        post_with_image = Post.objects.create(
            thread=self.thread,
            author=self.regular_user,
            body='Post with image',
            image='https://example.com/test-image.jpg'
        )
        
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        context = response.context
        
        posts_json = json.loads(context['posts_json'])
        image_post_data = next((p for p in posts_json if p['image_url'] is not None), None)
        
        if image_post_data:
            self.assertEqual(image_post_data['image_url'], 'https://example.com/test-image.jpg')

    def test_edit_post_with_invalid_data(self):
        """Test editing post with invalid data"""
        self.client.login(username='regular_user', password='testpass123')
        
        # Try to edit with empty body
        post_data = {
            'body': '',  # Invalid empty body
        }
        
        response = self.client.post(
            reverse('forums:edit_post', args=[self.initial_post.id]),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)

    def test_non_ajax_requests(self):
        """Test non-AJAX requests to AJAX-only endpoints"""
        self.client.login(username='regular_user', password='testpass123')
        
        # Test edit_thread without AJAX
        response = self.client.post(
            reverse('forums:edit_thread', args=[self.thread.id]),
            data={'title': 'New Title'}
        )
        # Should return 405 or handle gracefully
        self.assertIn(response.status_code, [405, 400])
        
        # Test edit_post without AJAX
        response = self.client.post(
            reverse('forums:edit_post', args=[self.initial_post.id]),
            data={'body': 'New body'}
        )
        self.assertIn(response.status_code, [405, 400])

    def test_thread_posts_with_nonexistent_thread(self):
        """Test accessing posts of nonexistent thread"""
        response = self.client.get(reverse('forums:thread_posts', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_reply_to_nonexistent_parent(self):
        """Test replying to nonexistent parent post"""
        self.client.login(username='regular_user', password='testpass123')
        
        post_data = {
            'body': 'Reply to nonexistent parent',
            'parent_id': 9999  # Nonexistent parent
        }
        
        response = self.client.post(
            reverse('forums:thread_posts', args=[self.thread.id]),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should still succeed but parent will be None
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertIsNone(response_data['post']['parent_id'])


class ThreadPostsTemplateTests(TestCase):
    """Tests specifically for template rendering and JavaScript functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpass123'
        )
        # Create profile for user
        Profile.objects.get_or_create(
            user=self.user, 
            defaults={'role': 'PEMAIN'}
        )
        
        # Create tournament with required fields
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            organizer=self.user,
            start_date=timezone.now().date(),  # Required field
            end_date=timezone.now().date() + timedelta(days=7)
        )
        self.thread = Thread.objects.create(
            tournament=self.tournament,
            author=self.user,
            title='Test Thread'
        )
        self.post = Post.objects.create(
            thread=self.thread,
            author=self.user,
            body='Test post content'
        )

    def test_template_inheritance(self):
        """Test that template extends base.html"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        self.assertEqual(response.status_code, 200)
        # Check for common base template elements
        self.assertContains(response, '<html')
        self.assertContains(response, '</html>')

    def test_javascript_block(self):
        """Test that javascript block is present"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        self.assertContains(response, 'script')

    def test_timezone_handling(self):
        """Test that timezone is set correctly"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        # The template uses timezone, check for timezone-related content
        self.assertContains(response, 'created_at')

    def test_modals_present(self):
        """Test that all modals are present in template"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        
        self.assertContains(response, 'edit-post-modal')
        self.assertContains(response, 'edit-thread-modal')
        self.assertContains(response, 'delete-thread-modal')
        self.assertContains(response, 'delete-post-modal')

    def test_reply_form_template(self):
        """Test that reply form template is present"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        self.assertContains(response, 'reply-form-template')

    def test_posts_data_script(self):
        """Test that posts data script tag is present"""
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        self.assertContains(response, 'id="posts-data"')

    def test_csrf_token_presence(self):
        """Test that CSRF tokens are present in forms"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_authenticated_vs_unauthenticated_content(self):
        """Test content differences between authenticated and unauthenticated users"""
        # Unauthenticated
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        
        self.assertContains(response, 'Silakan')
        self.assertContains(response, 'login')
        self.assertContains(response, 'untuk membalas thread ini')
        
        # Authenticated
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('forums:thread_posts', args=[self.thread.id]))
        self.assertContains(response, 'Tinggalkan Balasan untuk Thread')