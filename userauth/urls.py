from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile')
    # Test
]
