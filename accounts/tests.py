"""Pruebas de autenticación real del alumno y control de permisos."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from convocatorias.models import Convocatoria, TipoMovilidad
from expedientes.models import ExpedienteMovilidad


class AccesoMovilidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.alumno = user_model.objects.create_user(username="alumno_acceso", password="PruebaSegura1!")
        cls.otro = user_model.objects.create_user(username="otro_acceso", password="PruebaSegura1!")
        cls.responsable = user_model.objects.create_user(username="responsable_acceso", password="PruebaSegura1!", is_staff=True)
        cls.responsable.user_permissions.add(Permission.objects.get(codename="view_expedientemovilidad"))
        cls.tipo = TipoMovilidad.objects.create(nombre="Tipo de acceso")
        cls.convocatoria = Convocatoria.objects.create(tipo_movilidad=cls.tipo, titulo="Prueba acceso", ciclo="PRIMAVERA", anio=2027)
        cls.expediente = ExpedienteMovilidad.objects.create(alumno=cls.alumno, convocatoria=cls.convocatoria)

    def test_alumno_puede_iniciar_sesion_sin_staff(self):
        r = self.client.post(reverse("accounts:login"), {"username": "alumno_acceso", "password": "PruebaSegura1!"})
        self.assertRedirects(r, reverse("expedientes:lista"))
        self.assertFalse(self.alumno.is_staff)
        self.assertEqual(self.client.get(reverse("expedientes:detalle", args=[self.expediente.pk])).status_code, 200)

    def test_responsable_con_permiso_va_al_panel(self):
        r = self.client.post(reverse("accounts:login"), {"username": "responsable_acceso", "password": "PruebaSegura1!"})
        self.assertRedirects(r, reverse("expedientes:panel_responsable"))

    def test_otro_alumno_no_accede_expediente(self):
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(reverse("expedientes:detalle", args=[self.expediente.pk])).status_code, 404)

    def test_login_respetar_next_interno(self):
        url = reverse("expedientes:detalle", args=[self.expediente.pk])
        r = self.client.post(reverse("accounts:login"), {"username": "alumno_acceso", "password": "PruebaSegura1!", "next": url})
        self.assertRedirects(r, url)

    def test_login_no_redirigir_dominio_externo(self):
        r = self.client.post(reverse("accounts:login"), {"username": "alumno_acceso", "password": "PruebaSegura1!", "next": "https://example.org/"})
        self.assertRedirects(r, reverse("expedientes:lista"))

    def test_logout_requiere_post(self):
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("accounts:logout")), reverse("accounts:login"))
