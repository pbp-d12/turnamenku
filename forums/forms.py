from django import forms
from .models import Post, Thread

text_input_classes = 'w-full px-4 py-3 border border-custom-blue-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-custom-blue-300 focus:border-transparent transition-all duration-300 text-custom-blue-400 placeholder-custom-blue-200'
textarea_classes = text_input_classes + ' resize-vertical'
url_input_classes = 'w-full p-3 border border-custom-blue-100 rounded-lg text-custom-blue-400 focus:outline-none focus:ring-2 focus:ring-custom-blue-300 transition-all duration-300'


class ThreadCreateForm(forms.Form):
    title = forms.CharField(
        label="Judul Thread",
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'id': 'title',
            'class': text_input_classes,
            'placeholder': 'Masukkan judul yang jelas...'
        })
    )
    body = forms.CharField(
        label="Isi Postingan Pertama",
        required=True,
        widget=forms.Textarea(attrs={
            'id': 'body',
            'rows': 8,
            'class': textarea_classes,
            'placeholder': 'Tulis isi postingan Anda di sini...'
        })
    )
    image = forms.URLField(
        label="URL Gambar (Opsional)",
        required=False,
        widget=forms.URLInput(attrs={
            'id': 'image',
            'class': url_input_classes,
            'placeholder': 'https://example.com/image.png'
        })
    )

class ThreadEditForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': text_input_classes,
                'placeholder': 'Masukkan judul thread...'
            })
        }

class PostEditForm(forms.ModelForm):
    image = forms.URLField(
        label="URL Gambar (Opsional)",
        required=False,
        widget=forms.URLInput(attrs={
            'class': url_input_classes,
            'placeholder': 'https://example.com/image.png'
        })
    )

    class Meta:
        model = Post
        fields = ['body', 'image'] 
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 4,
                'class': textarea_classes.replace('px-4 py-3', 'p-3').replace('rounded-xl', 'rounded-lg'), 
                'placeholder': 'Tulis isi postingan...',
            }),
        }

class PostReplyForm(forms.ModelForm):
    image = forms.URLField(
        label="URL Gambar (Opsional)",
        required=False,
        widget=forms.URLInput(attrs={
            'class': url_input_classes,
            'placeholder': 'https://example.com/image.png'
        })
    )

    class Meta:
        model = Post
        fields = ['body', 'image']
        labels = {
            'body': 'Balasan Anda',
        }
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 4,
                'class': textarea_classes.replace('px-4 py-3', 'p-3').replace('rounded-xl', 'rounded-lg'),
                'placeholder': 'Tulis balasan kamu di sini...',
                'required': True
            }),
        }