from django.urls import path
from . import views




urlpatterns = [
    path("", views.index, name="index"),
    path("liste_media", views.media_list, name="media_list"),
    path('media/<int:pk>/', views.media_detail, name='media_detail'),
    path("emprunter/", views.borrowing_media, name="borrowing_media"),
    path("choisir_emprunt/", views.choose_borrow_to_return, name="choose_borrow"),
    path('retour/<int:borrow_id>/', views.returning_media, name='returning_media'),
    path("ajouter_media/", views.add_media, name="add_media"),
    path("liste_membres/", views.member_list, name="member_list"),
    path("membres/<int:member_id>", views.member_detail, name="member_detail"),
    path("ajouter_membre/", views.add_member, name="add_member"),
    path("mettre_a_jour_membre/<int:member_id>", views.update_member, name="update_member"),
    path('membres/<int:member_id>/supprimer/', views.delete_member, name='delete_member'),
]