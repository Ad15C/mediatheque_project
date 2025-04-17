from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.generic import TemplateView, CreateView, ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from personnel.models import Borrow, Member, Media, Livre, DVD, CD, JeuPlateau
from personnel.forms import MediaForm, MemberForm
from .services.error_service import handle_error
from .services.media_service import create_media
from .services.borrow_service import return_media
from .services.borrowing_rules_service import get_active_borrowing_rules
from .services.member_service import (add_member, update_member as update_member_service,
                                      delete_member)
from personnel.mixins import StaffRequiredMixin
from django.db import transaction




class CustomLoginView(auth_views.LoginView):
    template_name = 'login.html'

    def get_success_url(self):
        # Ignore le paramètre 'next' et redirige simplement vers l'index
        return reverse_lazy('index')


# Page d'accueil
@login_required
def index(request):
    # Votre logique pour la page d'accueil
    return render(request, 'personnel/index.html')


# Page de permission refusée
def permission_denied_view(request):
    return render(request, 'personnel/permission_denied.html', status=403)

def handle_error(request, error_message, redirect_url='member_error'):
    messages.error(request, error_message)
    return redirect(redirect_url)

# Ajouter un média
class MediaCreateView(StaffRequiredMixin, LoginRequiredMixin, CreateView):
    model = Media
    form_class = MediaForm
    template_name = 'personnel/add_media.html'
    success_url = reverse_lazy('media_list')

    def form_valid(self, form):
        try:
            media = create_media(form, form.cleaned_data['media_type'])
            messages.success(self.request, f"{media.name} a été ajouté avec succès!")
            return super().form_valid(form)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

# Liste des médias avec pagination et filtres
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def media_list(request):
    # Récupérer tous les médias de chaque type
    livres = Media.objects.filter(media_type='Livre')  # Exemple, adaptez selon votre modèle
    dvds = Media.objects.filter(media_type='DVD')
    cds = Media.objects.filter(media_type='CD')
    jeux_plateau = Media.objects.filter(media_type='Jeu de Plateau')

    return render(request, 'personnel/media_list.html', {
        'livres': livres,
        'dvds': dvds,
        'cds': cds,
        'jeux_plateau': jeux_plateau,
    })

# Détails d'un média
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def media_detail(request, pk):
    media = get_object_or_404(Media, pk=pk)
    borrows = Borrow.objects.filter(media=media).select_related('borrower')
    return render(request, 'personnel/media_detail.html', {'media': media, 'borrow_history': borrows})

# Emprunter un média
@login_required
@user_passes_test(lambda u: u.is_authenticated and u.member.can_borrow(), login_url='/login/')
def borrowing_media(request):
    try:
        member = request.user.member
    except Member.DoesNotExist:
        return handle_error(request, "Le membre n'existe pas.", 'member_error')

    if request.method == 'POST':
        media_id = request.POST.get('media_id')

        if not media_id:
            return handle_error(request, "Aucun média sélectionné.")

        try:
            selected_media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            return handle_error(request, "Média non trouvé.")

        # Vérification si le média est valide
        if selected_media is None:
            return handle_error(request, "Le média sélectionné est introuvable.")

        # Vérification si l'utilisateur a déjà un emprunt actif
        if Borrow.objects.filter(borrower=member, date_effective_return__isnull=True).exists():
            return handle_error(request, "Vous avez déjà un emprunt actif.")

        # Vérification des critères d'emprunt
        valid, error_message = member.check_borrow_criteria(selected_media)
        if not valid:
            return handle_error(request, error_message)

        # Création de l'emprunt
        with transaction.atomic():
            borrow = Borrow.objects.create(borrower=member, media=selected_media, user=request.user)
            borrow.confirm_borrow()

        messages.success(request, f"L'emprunt de {selected_media.name} a été effectué avec succès!")
        return redirect('borrowing_success', media_name=selected_media.name)

    # Chargement des médias disponibles
    available_media = Media.objects.filter(available=True)
    borrows = Borrow.objects.filter(borrower=member).select_related('media')

    return render(request, 'personnel/borrowing_media.html', {
        'available_media': available_media,
        'borrows': borrows,
        'member': member
    })


@login_required
def borrowing_success(request, media_name):
    return render(request, 'personnel/borrowing_success.html', {'media_name': media_name})


# Règles d'emprunt
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='no_permission')
def view_borrowing_rules(request):
    rules = get_active_borrowing_rules()
    return render(request, 'personnel/borrowing_rules.html', {'rules': rules})

# Retourner un emprunt
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='no_permission')
def returning_media_view(request, borrow_id):
    try:
        member = request.user.member
    except Member.DoesNotExist:
        return handle_error(request, "Le membre n'existe pas.", 'member_error')

    try:
        return return_media(borrow_id, member)
    except Borrow.DoesNotExist:
        return handle_error(request, "Emprunt non trouvé.")
    except Exception as e:
        return handle_error(request, f"Une erreur s’est produite : {str(e)}")

# Choisir un emprunt à retourner
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='no_permission')
def choose_borrow_to_return_view(request):
    try:
        member = request.user.member
    except Member.DoesNotExist:
        return handle_error(request, "Le membre n'existe pas.", 'member_error')

    borrows = Borrow.objects.filter(borrower=member, date_effective_return__isnull=True)
    return render(request, 'personnel/returning_media.html', {'borrows': borrows})

# Ajouter un membre
class MemberCreateView(StaffRequiredMixin, LoginRequiredMixin, CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'personnel/add_member.html'

    def form_valid(self, form):
        try:
            member = add_member(form)
            messages.success(self.request, "Membre ajouté avec succès!")
            return redirect('member_detail', pk=member.pk)
        except Exception as e:
            messages.error(self.request, f"Erreur : {e}")
            return self.form_invalid(form)

# Liste des membres
class MemberListView(ListView):
    model = Member
    template_name = 'personnel/member_list.html'
    context_object_name = 'members'

    def get_queryset(self):
        queryset = super().get_queryset()
        # Optionnel : ajouter des filtres ou une pagination personnalisée ici
        return queryset

# Détails d'un membre
class MemberDetailView(StaffRequiredMixin, LoginRequiredMixin, DetailView):
    model = Member
    template_name = 'personnel/member_detail.html'
    context_object_name = 'member'

# Mettre à jour un membre
class MemberUpdateView(StaffRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'personnel/update_member.html'
    context_object_name = 'member'

    def form_valid(self, form):
        try:
            updated_member = update_member_service(self.object, form.cleaned_data)
            messages.success(self.request, "Le membre a été mis à jour avec succès!")
            return redirect('member_detail', pk=self.object.pk)
        except Exception as e:
            messages.error(self.request, f"Une erreur est survenue : {str(e)}")
            return self.form_invalid(form)

# Suppression d'un membre
class MemberDeleteView(StaffRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Member
    template_name = 'personnel/confirm_delete_member.html'
    success_url = reverse_lazy('member_list')

    def delete(self, request, *args, **kwargs):
        member = self.get_object()
        try:
            delete_member(member.pk)
            messages.success(request, "Membre supprimé avec succès.")
        except Member.DoesNotExist:
            messages.error(request, "Le membre n'existe pas.")
        except Exception as e:
            messages.error(request, f"Une erreur est survenue : {str(e)}")
        return redirect(self.success_url)

# Membres en retard avec pagination
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='no_permission')
def members_overdue(request):
    overdue_members = Member.objects.filter(
        borrow__date_due__lt=timezone.now(),
        borrow__date_effective_return__isnull=True
    ).distinct()

    paginator = Paginator(overdue_members, 10)  # 10 membres par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'personnel/members_overdue.html', {
        'page_obj': page_obj,
        'now': timezone.now()
    })

# Vue erreur membre
def member_error(request):
    return render(request, 'personnel/member_error.html')
