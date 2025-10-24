from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from teams.models import Team
from teams.admin import TeamAdmin

class MockRequest:
    pass

class TeamAdminTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()

        self.admin_user = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='pass'
        )
        self.captain = User.objects.create_user(username='captain', password='pass')
        self.member1 = User.objects.create_user(username='member1', password='pass')
        self.member2 = User.objects.create_user(username='member2', password='pass')

        self.team = Team.objects.create(name='Alpha Team', captain=self.captain)
        self.team.members.add(self.member1, self.member2)

        self.model_admin = TeamAdmin(Team, self.site)

    def test_list_display(self):
        """Test list_display fields exist and are correct."""
        self.assertIn('name', self.model_admin.list_display)
        self.assertIn('captain', self.model_admin.list_display)
        self.assertIn('member_count', self.model_admin.list_display)

    def test_list_filter(self):
        """Ensure the list_filter is set correctly."""
        self.assertIn('captain', self.model_admin.list_filter)

    def test_search_fields(self):
        """Ensure search_fields includes name and captain__username."""
        self.assertIn('name', self.model_admin.search_fields)
        self.assertIn('captain__username', self.model_admin.search_fields)

    def test_filter_horizontal(self):
        """Ensure filter_horizontal includes members."""
        self.assertIn('members', self.model_admin.filter_horizontal)

    def test_ordering(self):
        """Ensure ordering is by name."""
        self.assertEqual(self.model_admin.ordering, ('name',))

    def test_member_count_method(self):
        """Ensure member_count returns correct count."""
        count = self.model_admin.member_count(self.team)
        self.assertEqual(count, 2)

    def test_member_count_description(self):
        """Ensure member_count has correct short_description."""
        self.assertEqual(self.model_admin.member_count.short_description, 'Total Members')