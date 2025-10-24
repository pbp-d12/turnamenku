from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from teams.models import Team
from teams.admin import TeamAdmin
from teams.views import *
from django.contrib.auth.models import AnonymousUser

class MockRequest:
    def __init__(self, user):
        self.user = user

class TeamViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.team = Team.objects.create(name='Test Team', captain=self.user)
        self.team.members.add(self.user)
    def test_delete_member_as_captain(self):
        request = self.factory.post(f'/teams/{self.team.id}/member/{self.user.username}/delete/')
        request.user = self.user
        response = delete_member(request, team_id=self.team.id, member_username=self.user.username)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'error', 'message': 'Kapten tidak dapat menghapus diri sendiri.'}
        )
        
    def test_leave_team_as_captain(self):
        request = self.factory.post(f'/teams/{self.team.id}/leave/')
        request.user = self.user
        response = leave_team(request, team_id=self.team.id)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'success'}
        )
        with self.assertRaises(Team.DoesNotExist):
            Team.objects.get(id=self.team.id)

    def test_leave_team_as_member(self):
        member_user = User.objects.create_user(username='memberuser', password='12345')
        self.team.members.add(member_user)
        request = self.factory.post(f'/teams/{self.team.id}/leave/')
        request.user = member_user
        response = leave_team(request, team_id=self.team.id)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'success'}
        )
        self.assertIn(member_user, self.team.members.all())
    
    def test_join_team(self):
        new_user = User.objects.create_user(username='newuser', password='12345')
        request = self.factory.post(f'/teams/{self.team.id}/join/')
        request.user = new_user
        response = join_team(request, team_id=self.team.id)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'success'}
        )
        self.assertIn(new_user, self.team.members.all())    
    
    def test_join_team_already_member(self):
        request = self.factory.post(f'/teams/{self.team.id}/join/')
        request.user = self.user
        response = join_team(request, team_id=self.team.id)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'error', 'message': 'Anda sudah menjadi anggota tim ini.'}
        )
    
    def test_edit_team_as_non_captain(self):
        non_captain_user = User.objects.create_user(username='noncaptain', password='12345')
        request = self.factory.post(f'/teams/{self.team.id}/edit/', {'name': 'Updated Team'})
        request.user = non_captain_user
        response = edit_team(request, team_id=self.team.id)
        self.assertEqual(response.status_code, 404)

    def test_edit_team_as_captain(self):
        request = self.factory.post(f'/teams/{self.team.id}/edit/', {'name': 'Updated Team'})
        request.user = self.user
        response = edit_team(request, team_id=self.team.id)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'success'}
        )
        self.team.refresh_from_db()
        self.assertEqual(self.team.name, 'Updated Team')

    def test_delete_team_as_captain(self):
        request = self.factory.post(f'/teams/{self.team.id}/delete/')
        request.user = self.user
        response = delete_team(request, team_id=self.team.id)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'success'}
        )
        with self.assertRaises(Team.DoesNotExist):
            Team.objects.get(id=self.team.id)

    def test_create_team(self):
        request = self.factory.post('/teams/create/', {'name': 'New Team'})
        request.user = self.user
        response = create_team(request)
        self.assertEqual(response.status_code, 200)
        response_data = {
            'status': 'success',
            'team_id': Team.objects.get(name='New Team').id
        }
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            response_data
        )
        new_team = Team.objects.get(name='New Team')
        self.assertEqual(new_team.captain, self.user)
        self.assertIn(self.user, new_team.members.all())

    def test_create_team_without_name(self):
        request = self.factory.post('/teams/create/', {})
        request.user = self.user
        response = create_team(request)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'error', 'message': 'Nama tim diperlukan.'}
        )
    
    def test_search_teams(self):
        request = self.factory.post('/teams/search/', {'query': 'Test'})
        request.user = self.user
        response = search_teams(request)
        self.assertEqual(response.status_code, 200)
        response_data = {
            'status': 'success',
            'teams': [
                {
                    'id': self.team.id,
                    'name': self.team.name,
                    'captain': self.team.captain.username,
                    'members_count': self.team.members.count(),
                }
            ]
        }
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            response_data
        )

    def test_search_teams_no_query(self):
        request = self.factory.post('/teams/search/', {})
        request.user = self.user
        response = search_teams(request)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'error', 'message': 'Query pencarian diperlukan.'}
        )

    def test_show_json(self):
        request = self.factory.get('/teams/json/')
        response = show_json(request)
        self.assertEqual(response.status_code, 200)
        response_data = {
            'status': 'success',
            'teams': [
                {
                    'id': self.team.id,
                    'name': self.team.name,
                    'captain': self.team.captain.username,
                    'members_count': self.team.members.count(),
                }
            ]
        }
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            response_data
        )

    def test_team_detail_json(self):
        request = self.factory.get(f'/teams/json/{self.team.id}/')
        response = team_detail_json(request, team_id=self.team.id)
        self.assertEqual(response.status_code, 200)
        response_data = {
            'status': 'success',
            'team': {
                'id': self.team.id,
                'name': self.team.name,
                'captain': self.team.captain.username,
                'members': list(self.team.members.values('id', 'username')),
            }
        }
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            response_data
        )
    
    def test_team_detail_json_not_found(self):
        request = self.factory.get('/teams/json/9999/')
        response = team_detail_json(request, team_id=9999)
        self.assertEqual(response.status_code, 404)
    
        self.assertJSONEqual(
            str(response.content, encoding='utf8'),
            {'status': 'error', 'message': 'Tim tidak ditemukan.'}
        )
    
    def test_show_main_teams_anonymous(self):
        request = self.factory.get('/teams/')
        request.user = AnonymousUser()
        response = show_main_teams(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('teams', response.context_data)

    def test_show_main_teams_authenticated(self):
        request = self.factory.get('/teams/')
        request.user = self.user
        response = show_main_teams(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('teams', response.context_data)
        self.assertIn('user', response.context_data)
        self.assertEqual(response.context_data['user'], self.user)


        