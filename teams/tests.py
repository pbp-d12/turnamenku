from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Team

class TeamsViewsTestCase(TestCase):
    def setUp(self):
        # Setup data test reusable
        self.client = Client()
        
        # Buat users
        self.user = User.objects.create_user(username='user', password='pass123')
        self.captain = User.objects.create_user(username='captain', password='pass123')
        self.superuser = User.objects.create_superuser(username='superuser', password='pass123')
        self.other_user = User.objects.create_user(username='other', password='pass123')
        
        # Buat teams
        self.team1 = Team.objects.create(name='Team 1', captain=self.captain)
        self.team1.members.add(self.captain, self.user)
        self.team2 = Team.objects.create(name='Team 2', captain=self.superuser)
        self.team2.members.add(self.superuser)
    
    # Test untuk show_main_teams
    def test_show_main_teams_authenticated(self):
        self.client.login(username='user', password='pass123')
        response = self.client.get(reverse('teams:show_main_teams'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teams.html')
        self.assertIn('teams', response.context)
    
    def test_show_main_teams_unauthenticated(self):
        response = self.client.get(reverse('teams:show_main_teams'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['user'])
    
    # Test untuk search_teams
    def test_search_teams_join_mode_authenticated(self):
        self.client.login(username='user', password='pass123')
        response = self.client.get(reverse('teams:search_teams') + '?mode=join&q=Team')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertGreater(len(data['results']), 0)
    
    def test_search_teams_meet_mode_authenticated(self):
        self.client.login(username='user', password='pass123')
        response = self.client.get(reverse('teams:search_teams') + '?mode=meet')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
    
    def test_search_teams_manage_mode_captain(self):
        self.client.login(username='captain', password='pass123')
        response = self.client.get(reverse('teams:search_teams') + '?mode=manage')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
    
    def test_search_teams_manage_mode_superuser(self):
        self.client.login(username='superuser', password='pass123')
        response = self.client.get(reverse('teams:search_teams') + '?mode=manage')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        # Superuser harus lihat semua teams
    
    def test_search_teams_invalid_mode(self):
        self.client.login(username='user', password='pass123')
        response = self.client.get(reverse('teams:search_teams') + '?mode=invalid')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_search_teams_unauthenticated_non_join(self):
        response = self.client.get(reverse('teams:search_teams') + '?mode=meet')
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    # Test untuk create_team
    def test_create_team_success(self):
        self.client.login(username='user', password='pass123')
        response = self.client.post(reverse('teams:create_team'), {'name': 'New Team'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(Team.objects.filter(name='New Team').exists())
    
    def test_create_team_no_name(self):
        self.client.login(username='user', password='pass123')
        response = self.client.post(reverse('teams:create_team'), {})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_create_team_unauthenticated(self):
        response = self.client.post(reverse('teams:create_team'), {'name': 'New Team'})
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    # Test untuk join_team
    def test_join_team_success(self):
        self.client.login(username='other', password='pass123')
        response = self.client.post(reverse('teams:join_team', kwargs={'team_id': self.team1.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.team1.refresh_from_db()
        self.assertIn(self.other_user, self.team1.members.all())
    
    def test_join_team_already_member(self):
        self.client.login(username='user', password='pass123')
        response = self.client.post(reverse('teams:join_team', kwargs={'team_id': self.team1.id}))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_join_team_invalid_id(self):
        self.client.login(username='user', password='pass123')
        response = self.client.post(reverse('teams:join_team', kwargs={'team_id': 999}))
        self.assertEqual(response.status_code, 404)
    
    # Test untuk edit_team
    def test_edit_team_success_captain(self):
        self.client.login(username='captain', password='pass123')
        response = self.client.post(reverse('teams:edit_team', kwargs={'team_id': self.team1.id}), {'name': 'Edited Team'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.team1.refresh_from_db()
        self.assertEqual(self.team1.name, 'Edited Team')
    
    def test_edit_team_not_captain(self):
        self.client.login(username='user', password='pass123')
        response = self.client.post(reverse('teams:edit_team', kwargs={'team_id': self.team1.id}), {'name': 'Edited Team'})
        self.assertEqual(response.status_code, 404)  # get_object_or_404 gagal
    
    def test_edit_team_superuser(self):
        self.client.login(username='superuser', password='pass123')
        response = self.client.post(reverse('teams:edit_team', kwargs={'team_id': self.team1.id}), {'name': 'Edited by Super'})
        self.assertEqual(response.status_code, 404)  # Karena superuser bukan captain, tapi bisa kita modifikasi view jika perlu
    
    # Test untuk delete_team
    def test_delete_team_success_captain(self):
        self.client.login(username='captain', password='pass123')
        response = self.client.post(reverse('teams:delete_team', kwargs={'team_id': self.team1.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertFalse(Team.objects.filter(id=self.team1.id).exists())
    
    def test_delete_team_not_captain(self):
        self.client.login(username='user', password='pass123')
        response = self.client.post(reverse('teams:delete_team', kwargs={'team_id': self.team1.id}))
        self.assertEqual(response.status_code, 404)
    
    # Test untuk leave_team
    def test_leave_team_member(self):
        self.client.login(username='user', password='pass123')
        response = self.client.post(reverse('teams:leave_team', kwargs={'team_id': self.team1.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.team1.refresh_from_db()
        self.assertNotIn(self.user, self.team1.members.all())
    
    def test_leave_team_captain(self):
        self.client.login(username='captain', password='pass123')
        response = self.client.post(reverse('teams:leave_team', kwargs={'team_id': self.team1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Team.objects.filter(id=self.team1.id).exists())  # Team dihapus jika captain leave
    
    # Test untuk delete_member (sudah lengkap dari sebelumnya, tapi tambah edge cases)
    def test_delete_member_captain_success(self):
        self.client.login(username='captain', password='pass123')
        response = self.client.post(reverse('teams:delete_member', kwargs={'team_id': self.team1.id, 'member_username': self.user.username}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.team1.refresh_from_db()
        self.assertNotIn(self.user, self.team1.members.all())
    
    def test_delete_member_superuser_success(self):
        self.client.login(username='superuser', password='pass123')
        response = self.client.post(reverse('teams:delete_member', kwargs={'team_id': self.team1.id, 'member_username': self.user.username}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
    
    def test_delete_member_captain_self(self):
        self.client.login(username='captain', password='pass123')
        response = self.client.post(reverse('teams:delete_member', kwargs={'team_id': self.team1.id, 'member_username': self.captain.username}))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_delete_member_not_captain(self):
        self.client.login(username='other', password='pass123')
        response = self.client.post(reverse('teams:delete_member', kwargs={'team_id': self.team1.id, 'member_username': self.user.username}))
        self.assertEqual(response.status_code, 404)
    
    # Test untuk show_json
    def test_show_json(self):
        response = self.client.get(reverse('teams:show_json'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
