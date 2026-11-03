"""Regresión de presentación: no se filtran datos ni se alteran reglas."""
from django.test import SimpleTestCase
from django.template import Context, Template
from expedientes.templatetags.actividades_presentacion import evidencia_actividad

MATRIZ = (
    "Paso 11 de 27 — Matriz institucional original.\n"
    "Responsable original: DAAE\n"
    "Documento / evidencia: Expediente de postulación\n"
    "Quién recibe o interviene: IES destino\n"
    "Condición para avanzar (matriz): Postulación enviada\n"
    "Estado propuesto originalmente: POSTULADO_IES\n"
    "Obligatoriedad técnica: pendiente de parametrización por convocatoria."
)

class PresentacionActividadesTests(SimpleTestCase):
    def test_matriz_muestra_evidencia_y_no_notas_tecnicas(self):
        self.assertEqual(evidencia_actividad(MATRIZ), "Expediente de postulación")
        html = Template("{% load actividades_presentacion %}{{ descripcion|evidencia_actividad }}").render(Context({"descripcion": MATRIZ}))
        self.assertNotIn("Obligatoriedad técnica", html)
        self.assertNotIn("Estado propuesto", html)
        self.assertIn("Expediente de postulación", html)

    def test_evidencia_no_documental_se_oculta(self):
        texto = "Paso 1 de 27 — Matriz institucional original.\nDocumento / evidencia: No necesariamente documento"
        self.assertEqual(evidencia_actividad(texto), "")

    def test_descripcion_manual_se_conserva(self):
        self.assertEqual(evidencia_actividad("Completar el formulario y presentarlo."), "Completar el formulario y presentarlo.")
        self.assertEqual(evidencia_actividad(""), "")

    def test_plantilla_y_css_independiente(self):
        from pathlib import Path
        from django.conf import settings
        root = Path(settings.BASE_DIR)
        plantilla = (root / "expedientes/templates/expedientes/detalle_expediente.html").read_text(encoding="utf-8")
        css = (root / "expedientes/static/expedientes/actividades.css").read_text(encoding="utf-8")
        self.assertIn("|evidencia_actividad", plantilla)
        self.assertIn("expedientes/actividades.css", plantilla)
        self.assertNotIn("{{ actividad.actividad_proceso.descripcion }}", plantilla)
        self.assertIn("overflow-wrap:anywhere", css)
