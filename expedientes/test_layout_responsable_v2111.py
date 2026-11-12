from pathlib import Path
from django.test import SimpleTestCase


class EstructuraVisualResponsableTests(SimpleTestCase):
    def test_css_contiene_estructura_y_personalizacion(self):
        ruta = Path(__file__).resolve().parent / "static" / "expedientes" / "centro_gestion_v210.css"
        css = ruta.read_text(encoding="utf-8")
        estructura = [
            ".cg-header {height:76px;display:flex",
            ".cg-brand {display:flex",
            ".cg-header-tools {display:flex",
            ".cg-layout {display:grid",
            ".cg-sidebar {background:",
            ".cg-nav-item,.cg-nav-future {display:flex",
            ".cg-main {padding:",
            ".cg-metrics{display:grid",
            ".cg-tabs{display:flex",
        ]
        for regla in estructura:
            with self.subTest(regla=regla):
                self.assertIn(regla, css)

    def test_base_responsable_carga_css(self):
        ruta = Path(__file__).resolve().parent / "templates" / "expedientes" / "base_responsable.html"
        html = ruta.read_text(encoding="utf-8")
        self.assertIn("expedientes/centro_gestion_v210.css", html)
