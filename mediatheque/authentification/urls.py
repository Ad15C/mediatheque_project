from django.urls import path
from . import views

app_name = 'authentification'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('staff_dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('client_dashboard/', views.client_dashboard, name='client_dashboard'),
]
