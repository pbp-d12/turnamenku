from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.forms import AuthenticationForm as LoginForm
from .models import Profile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Email wajib diisi.")
    role = forms.ChoiceField(
        choices=Profile.REGISTRATION_ROLE_CHOICES,
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
                if '1' in field_name or field_name == 'password':
                    self.fields[field_name].label = "Kata Sandi"
                elif '2' in field_name or 'confirmation' in field_name:
                    self.fields[field_name].label = "Konfirmasi Kata Sandi"
                self.fields[field_name].help_text = None

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            role = self.cleaned_data.get('role')
            Profile.objects.create(user=user, role=role)
        return user


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = "Nama Pengguna"
        self.fields['password'].label = "Kata Sandi"


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label="Alamat Email")

    class Meta:
        model = User
        fields = ['username', 'email']
        labels = {'username': 'Nama Pengguna'}
        help_texts = {'username': "Nama pengguna tidak bisa diubah."}

    def __init__(self, *args, **kwargs):
        super(UserUpdateForm, self).__init__(*args, **kwargs)
        if 'username' in self.fields:
            self.fields['username'].disabled = True


class ProfileUpdateForm(forms.ModelForm):
    profile_picture = forms.URLField(label='URL Foto Profil', required=False,
                                     widget=forms.URLInput(attrs={'placeholder': 'https://example.com/image.png'}))
    bio = forms.CharField(label='Biografi', required=False, widget=forms.Textarea(
        attrs={'rows': 4}))

    class Meta:
        model = Profile
        fields = ['role', 'bio', 'profile_picture']
        labels = {
            'role': 'Peran Akun'
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance').user if kwargs.get('instance') else None
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)

        if 'role' in self.fields and user and not user.is_superuser:
            allowed_choices = Profile.REGISTRATION_ROLE_CHOICES

            self.fields['role'].choices = allowed_choices


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = "Kata Sandi Lama"
        self.fields['old_password'].help_text = None
        self.fields['new_password1'].label = "Kata Sandi Baru"
        self.fields['new_password1'].help_text = None
        self.fields['new_password2'].label = "Konfirmasi Kata Sandi Baru"
        self.fields['new_password2'].help_text = None
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({
                'class': 'block w-full px-4 py-2 mt-1 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-2 focus:ring-custom-blue-300 focus:border-custom-blue-300 transition duration-150 ease-in-out'
            })

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance').user if kwargs.get('instance') else None
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        if 'role' in self.fields and user and not user.is_superuser:
            allowed_choices = Profile.REGISTRATION_ROLE_CHOICES
            self.fields['role'].choices = allowed_choices
