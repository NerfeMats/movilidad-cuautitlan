"""V21.0: comprobaciones estructurales sin alterar datos ni permisos."""
from pathlib import Path
from django.test import SimpleTestCase
from django.template.loader import get_template

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates" / "expedientes"


class NavegacionResponsableV210Tests(SimpleTestCase):
    def test_vistas_administrativas_usan_base_independiente(self):
        for nombre in (
            "panel_responsable.html", "centro_seguimiento.html",
            "ruta_responsable.html", "inventario_documental.html",
        ):
            with self.subTest(plantilla=nombre):
                self.assertIn(
                    '{% extends "expedientes/base_responsable.html" %}',
                    (TPL / nombre).read_text(encoding="utf-8"),
                )
                get_template("expedientes/" + nombre)

    def test_portal_publico_sigue_separado(self):
        contenido = (TPL / "base_responsable.html").read_text(encoding="utf-8")
        self.assertIn("{% url 'inicio' %}", contenido)
        self.assertIn("{% url 'expedientes:centro_seguimiento' %}", contenido)
        self.assertNotIn("{% extends \"base.html\" %}", contenido)

    def test_vistas_estudiante_no_se_modifican(self):
        for nombre in ("lista_expedientes.html", "detalle_expediente.html"):
            self.assertIn(
                '{% extends "base.html" %}',
                (TPL / nombre).read_text(encoding="utf-8"),
            )

    def test_estudiante_conserva_enlace_a_ruta_y_documentos(self):
        html = (TPL / "ruta_responsable.html").read_text(encoding="utf-8")
        self.assertIn("Usted está aquí", html)
        self.assertIn("inventario_documental_responsable", html)

    def test_areas_futuras_no_tienen_enlaces_ficticios(self):
        html = (TPL / "base_responsable.html").read_text(encoding="utf-8")
        self.assertIn("Documentos y oficios", html)
        self.assertIn("Reportes", html)
        self.assertNotIn('href="#"', html)
