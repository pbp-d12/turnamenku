from django import forms
from .models import Post, Thread

class ThreadCreateForm(forms.Form):
    title = forms.CharField(
        label="Judul Thread", 
        max_length=255, 
        required=True,
        widget=forms.TextInput(attrs={
            'id': 'title', 
            'class': 'w-full px-4 py-3 border border-custom-blue-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-custom-blue-300 focus:border-transparent transition-all duration-300 text-custom-blue-400 placeholder-custom-blue-200',
            'placeholder': 'Masukkan judul yang jelas...'
        })
    )
    body = forms.CharField(
        label="Isi Postingan Pertama", 
        required=True,
        widget=forms.Textarea(attrs={
            'id': 'body', 
            'rows': 8,
            'class': 'w-full px-4 py-3 border border-custom-blue-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-custom-blue-300 focus:border-transparent transition-all duration-300 text-custom-blue-400 placeholder-custom-blue-200 resize-vertical',
            'placeholder': 'Tulis isi postingan Anda di sini...'
        })
    )
    image = forms.ImageField(
        label="Unggah Gambar (Opsional)",
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'id': 'image', 
            'class': 'w-full p-3 border border-custom-blue-100 rounded-lg text-custom-blue-400 focus:outline-none focus:ring-2 focus:ring-custom-blue-300 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-custom-blue-50 file:text-custom-blue-400 hover:file:bg-custom-blue-100'
        })
    )

class ThreadEditForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-custom-blue-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-custom-blue-300 focus:border-transparent transition-all duration-300 text-custom-blue-400',
                'placeholder': 'Masukkan judul thread...'
            })
        }

class PostEditForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['body', 'image']
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full p-3 border border-custom-blue-100 rounded-lg text-custom-blue-400 focus:outline-none focus:ring-2 focus:ring-custom-blue-300 transition-all duration-300',
                'placeholder': 'Tulis isi postingan...',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'w-full p-3 border border-custom-blue-100 rounded-lg text-custom-blue-400 focus:outline-none focus:ring-2 focus:ring-custom-blue-300 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-custom-blue-50 file:text-custom-blue-400 hover:file:bg-custom-blue-100'
            })
        }

class PostReplyForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['body', 'image'] 
        labels = {
            'body': 'Balasan Anda',
            'image': 'Unggah Gambar (Opsional)'
        }
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'w-full p-3 border border-custom-blue-100 rounded-lg text-custom-blue-400 focus:outline-none focus:ring-2 focus:ring-custom-blue-300 transition-all duration-300',
                'placeholder': 'Tulis balasan kamu di sini...',
                'required': True 
            }),
             'image': forms.ClearableFileInput(attrs={
                'class': 'w-full p-3 border border-custom-blue-100 rounded-lg text-custom-blue-400 focus:outline-none focus:ring-2 focus:ring-custom-blue-300 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-custom-blue-50 file:text-custom-blue-400 hover:file:bg-custom-blue-100'
            })
        }