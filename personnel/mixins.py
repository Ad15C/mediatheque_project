# contient des classes réutilisables pour la gestion
# des permissions ou d'autres logiques réutilisables

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Un mixin qui assure que l'utilisateur est connecté et qu'il est un membre du personnel.
    """
    def test_func(self):
        return self.request.user.is_staff