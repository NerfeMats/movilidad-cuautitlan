"""Regresion de la vista del responsable; solo lectura, sin base de datos."""
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase
from django.template import Context, Template

ROOT = Path(settings.BASE_DIR)

class PresentacionResponsableTests(SimpleTestCase):
    def test_no_imprime_descripcion_tecnica_directamente(self):
        html = (ROOT / "expedientes/templates/expedientes/ruta_responsable.html").read_text(encoding="utf-8")
        self.assertIn("{% load static actividades_presentacion %}", html)
        self.assertIn("|evidencia_actividad", html)
        self.assertNotIn("{{ a.actividad_proceso.descripcion }}", html)
        self.assertNotIn("Obligatoria: {% if", html)
        self.assertIn("{% if a.actividad_proceso.obligatorio %}", html)
        self.assertIn("Obligatoria: Sí", html)
        self.assertNotIn("<strong>Obligatoria:</strong> Sí", html)

    def test_extrae_evidencia_sin_notas_internas(self):
        entrada = ("Paso 5 de 27 — Matriz institucional original.\n"
                   "Documento / evidencia: Carta de Homologación Preliminar\n"
                   "Estado propuesto originalmente: HOMOLOGACION_EN_VALIDACION\n"
                   "Obligatoriedad técnica: pendiente de parametrización por convocatoria.")
        render = Template("{% load actividades_presentacion %}{{ texto|evidencia_actividad }}").render(Context({"texto": entrada}))
        self.assertEqual(render, "Carta de Homologación Preliminar")

    def test_css_externo_y_sin_cambios_al_mapa(self):
        html = (ROOT / "expedientes/templates/expedientes/ruta_responsable.html").read_text(encoding="utf-8")
        css = (ROOT / "expedientes/static/expedientes/ruta_actividades.css").read_text(encoding="utf-8")
        self.assertIn("ruta_actividades.css", html)
        self.assertIn("mapa_3d.css", html)
        self.assertIn("overflow-wrap:anywhere", css)
        self.assertNotIn('style="', html)
