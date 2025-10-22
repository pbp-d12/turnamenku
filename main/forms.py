from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm as LoginForm

from .models import Profile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Email wajib diisi.")
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        required=True,
        label="Daftar sebagai"
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super(UserRegisterForm, self).__init__(*args, **kwargs)
        for field_name in ['password', 'password1', 'password2', 'new_password1', 'new_password2', 'password_confirmation']:
            if field_name in self.fields:
                self.fields[field_name].help_text = None

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            role = self.cleaned_data.get('role')
            Profile.objects.create(user=user, role=role)
        return user


class UserUpdateForm(forms.ModelForm):
    """
    Form untuk mengedit data User (username, email).
    """
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super(UserUpdateForm, self).__init__(*args, **kwargs)
        if 'username' in self.fields:
            self.fields['username'].disabled = True
            self.fields['username'].help_text = "Username cannot be changed."


class ProfileUpdateForm(forms.ModelForm):
    """
    Form untuk mengedit data Profile (bio, foto, role).
    """
    class Meta:
        model = Profile
        fields = ['role', 'bio', 'profile_picture']
        labels = {
            'bio': 'Bio',
            'profile_picture': 'Foto Profil',
            'role': 'Role'
        }
        widgets = {
            'profile_picture': forms.FileInput(),
        }
