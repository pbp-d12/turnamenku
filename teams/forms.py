from django.forms import ModelForm
from teams.models import Team

class TeamEntryForm(ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'logo']  