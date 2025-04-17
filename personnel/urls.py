from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import (MediaCreateView, CustomLoginView, MemberListView, MemberDetailView,
                    MemberCreateView,MemberUpdateView, MemberDeleteView, borrowing_media,
                    choose_borrow_to_return_view, returning_media_view, members_overdue,
                    member_error, view_borrowing_rules, borrowing_success)



urlpatterns = [
    # Accueil & Authentification
    path("", views.index, name="index"),
    path('login/', CustomLoginView.as_view(), name='login'),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path('no-permission/', views.permission_denied_view, name='no_permission'),

    # Médias
    path("liste_media/", views.media_list, name="media_list"),
    path("media/<int:pk>/", views.media_detail, name="media_detail"),
    path("ajouter_media/", MediaCreateView.as_view(), name="add_media"),

    # Emprunts
    path("emprunter/", borrowing_media, name="borrowing_media"),
    path("choisir_emprunt/", choose_borrow_to_return_view, name="choose_borrow_to_return_view"),
    path("emprunt/confirmation/", views.borrowing_success, name="borrowing_success"),
    path("retour/<int:borrow_id>/", returning_media_view, name="returning_media"),

    # Membres
    path("liste_membres/", MemberListView.as_view(), name="member_list"),
    path("membres/<int:pk>/", MemberDetailView.as_view(), name="member_detail"),
    path("ajouter_membre/", MemberCreateView.as_view(), name="add_member"),
    path("mettre_a_jour_membre/<int:pk>/", MemberUpdateView.as_view(), name="update_member"),
    path("membres/<int:pk>/supprimer/", MemberDeleteView.as_view(), name="delete_member"),
    path("membres/retard/", members_overdue, name="members_overdue"),
    path("erreur-membre/", member_error, name="member_error"),

    # Règles d'emprunt
    path("regles_emprunt/", view_borrowing_rules, name="view_borrowing_rules"),
]
