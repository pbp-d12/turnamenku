from django.urls import path
from . import views # (Meskipun views.py masih kosong, ini tidak apa-apa)

app_name = 'tournaments' # Tambahkan ini untuk namespace

# Ini WAJIB ADA, meskipun masih kosong
urlpatterns = [
    # path('', views.index, name='index'), # Contoh path, bisa kamu uncomment nanti
]