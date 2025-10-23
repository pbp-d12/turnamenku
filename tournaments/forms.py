from django import forms
from .models import Tournament

class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        # Exclude 'organizer' (set in view) and 'participants' (managed separately)
        fields = ['name', 'description', 'banner', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Nama Turnamen'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Deskripsi singkat turnamen...'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'banner': forms.URLInput(attrs={'placeholder': 'https://example.com/banner.jpg'}),
        }
        labels = { # Optional: Prettier labels
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