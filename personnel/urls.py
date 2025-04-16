from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Accueil & Authentification
    path("", views.index, name="index"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("no-permission/", views.permission_denied_view, name="no_permission"),

    # Médias
    path("liste_media/", views.media_list, name="media_list"),
    path("media/<int:pk>/", views.media_detail, name="media_detail"),
    path("ajouter_media/", views.add_media, name="add_media"),

    # Emprunts
    path("emprunter/", views.borrowing_media, name="borrowing_media"),
    path("choisir_emprunt/", views.choose_borrow_to_return_view, name="choose_borrow_to_return_view"),
    path("retour/<int:borrow_id>/", views.returning_media_view, name="returning_media"),

    # Membres
    path("liste_membres/", views.member_list_view, name="member_list"),
    path("membres/<int:pk>/", views.member_detail_view, name="member_detail"),
    path("ajouter_membre/", views.add_member_view, name="add_member"),
    path("mettre_a_jour_membre/<int:pk>/", views.update_member_view, name="update_member"),
    path("membres/<int:pk>/supprimer/", views.delete_member_view, name="delete_member"),
    path("membres/retard/", views.members_overdue, name="members_overdue"),
    path("erreur-membre/", views.member_error, name="member_error"),

    # Règles d'emprunt
    path("regles_emprunt/", views.view_borrowing_rules, name="view_borrowing_rules"),
]
