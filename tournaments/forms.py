from django import forms
from .models import Tournament
from teams.models import Team 

class TournamentForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=Team.objects.all().order_by('name'), 
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-1'}), #
        required=False, # Buat opsional, turnamen bisa dibuat tanpa peserta awal
        label="Tim Peserta"
    )

    class Meta:
        model = Tournament
        fields = ['name', 'description', 'banner', 'start_date', 'end_date', 'participants']
        # ----------------------------------------------------
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Nama Turnamen'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Deskripsi singkat turnamen...'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'banner': forms.URLInput(attrs={'placeholder': 'https://example.com/banner.jpg'}),
        }
        labels = {
            'name': 'Nama Turnamen',
            'description': 'Deskripsi',
            'banner': 'URL Banner (Opsional)',
            'start_date': 'Tanggal Mulai',
            'end_date': 'Tanggal Selesai',
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("Tanggal selesai tidak boleh sebelum tanggal mulai.")

        return cleaned_data