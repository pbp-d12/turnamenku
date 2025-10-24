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

        selected_role = self.cleaned_data.get('role')
        user._registration_role = selected_role

        if commit:
            user.save()

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

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('user', None)
        super(UserUpdateForm, self).__init__(*args, **kwargs)
        if 'username' in self.fields and self.instance:
            is_editing_superuser = self.instance.is_superuser
            is_requester_superuser = self.request_user and self.request_user.is_superuser
            if is_editing_superuser:
                self.fields['username'].disabled = True
                self.fields['username'].help_text = "Nama pengguna Admin tidak dapat diubah."
            elif is_requester_superuser:
                self.fields['username'].disabled = False
                self.fields['username'].help_text = "Admin dapat mengubah nama pengguna ini."
            else:
                self.fields['username'].disabled = True
                self.fields['username'].help_text = "Nama pengguna tidak bisa diubah."
        elif 'username' in self.fields:
            self.fields['username'].disabled = True
            self.fields['username'].help_text = "Nama pengguna tidak bisa diubah."


class ProfileUpdateForm(forms.ModelForm):
    profile_picture = forms.URLField(label='URL Foto Profil', required=False,
                                     widget=forms.URLInput(attrs={'placeholder': 'https://example.com/image.png'}))
    bio = forms.CharField(label='Biografi', required=False,
                          widget=forms.Textarea(attrs={'rows': 4}))

    class Meta:
        model = Profile
        fields = ['role', 'bio', 'profile_picture']
        labels = {'role': 'Peran Akun'}
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)

        user_being_edited = self.instance.user if self.instance else None
        request_user = request.user if request else None

        if 'role' in self.fields and user_being_edited and request_user:
            if user_being_edited.is_superuser:
                self.fields['role'].disabled = True
                self.fields['role'].help_text = "Peran Admin tidak dapat diubah."
            elif not request_user.is_superuser:
                if request_user == user_being_edited:
                    allowed_choices = Profile.REGISTRATION_ROLE_CHOICES
                    self.fields['role'].choices = allowed_choices
                else:
                    # User biasa mencoba edit orang lain? Seharusnya dicegah view, tapi disable saja
                    self.fields['role'].disabled = True


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
