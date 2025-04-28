from django.urls import path
from . import views

app_name = 'authentification'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('modifier_profil/', views.edit_profile, name='modifier_profil'),
    path('espace_staff/', views.staff_dashboard, name='espace_staff'),
    path('espace_client/', views.client_dashboard, name='espace_client'),
]
