"""Acceso de alumnos y responsables sin conceder permisos de administración."""
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse


class AccesoMovilidad(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        user = self.request.user
        if user.is_staff and user.has_perm("expedientes.view_expedientemovilidad"):
            return reverse("expedientes:panel_responsable")
        return reverse("expedientes:lista")


class SalidaMovilidad(LogoutView):
    next_page = "accounts:login"
