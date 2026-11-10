"""Pruebas de regresión para la vista consultiva v20.5."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class DiagnosticoReglasV205Tests(TestCase):
    def setUp(self):
        self.url = reverse("expedientes:centro_seguimiento")
        self.usuario = get_user_model().objects.create_user(
            username="operador_v205", password="ClaveTemporalSegura_205", is_staff=True,
        )

    def test_exige_autenticacion(self):
        respuesta = self.client.get(self.url + "?vista=reglas")
        self.assertEqual(respuesta.status_code, 302)

    def test_exige_autorizacion_global(self):
        self.client.force_login(self.usuario)
        with patch("expedientes.panel_responsable.es_responsable_autorizado", return_value=False):
            respuesta = self.client.get(self.url + "?vista=reglas")
        self.assertEqual(respuesta.status_code, 403)

    def test_sin_seleccion_no_ejecuta_evaluador(self):
        self.client.force_login(self.usuario)
        with (patch("expedientes.panel_responsable.es_responsable_autorizado", return_value=True),
              patch("expedientes.evaluador_reglas.evaluar_etapa_expediente") as evaluar):
            respuesta = self.client.get(self.url + "?vista=reglas")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Diagnóstico consultivo de reglas")
        self.assertContains(respuesta, "Seleccione un expediente")
        evaluar.assert_not_called()

    def test_id_invalido_no_ejecuta_evaluador(self):
        self.client.force_login(self.usuario)
        with (patch("expedientes.panel_responsable.es_responsable_autorizado", return_value=True),
              patch("expedientes.evaluador_reglas.evaluar_etapa_expediente") as evaluar):
            respuesta = self.client.get(self.url + "?vista=reglas&expediente=abc")
        self.assertEqual(respuesta.status_code, 200)
        evaluar.assert_not_called()

    def test_id_inexistente_no_ejecuta_evaluador(self):
        self.client.force_login(self.usuario)
        with (patch("expedientes.panel_responsable.es_responsable_autorizado", return_value=True),
              patch("expedientes.evaluador_reglas.evaluar_etapa_expediente") as evaluar):
            respuesta = self.client.get(self.url + "?vista=reglas&expediente=99999999")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se encontró un expediente activo")
        evaluar.assert_not_called()

    def test_vistas_previas_conservadas(self):
        self.client.force_login(self.usuario)
        with patch("expedientes.panel_responsable.es_responsable_autorizado", return_value=True):
            for ruta in ("", "?vista=inventario"):
                respuesta = self.client.get(self.url + ruta)
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, "Diagnóstico de reglas")
