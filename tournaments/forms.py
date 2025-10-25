from django import forms
from .models import Tournament
from teams.models import Team

class TournamentForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=Team.objects.all(), 
        widget=forms.SelectMultiple(attrs={'hidden': True}),
        required=False,
        label="Tim Peserta"
    )
    registration_open = forms.BooleanField(
        required=False, 
        label="Buka Pendaftaran Tim",
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-custom-blue-400 border-gray-300 rounded focus:ring-custom-blue-300'})
    )

    class Meta:
        model = Tournament
        fields = ['name', 'description', 'banner', 'start_date', 'end_date', 'participants', 'registration_open']
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