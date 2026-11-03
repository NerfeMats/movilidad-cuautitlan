"""Regresión estructural de plantillas y estáticos, sin datos de producción."""
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase

ROOT = Path(settings.BASE_DIR)


class FrontendEstructuraTests(SimpleTestCase):
    def test_paginas_convocatoria_usan_base_comun(self):
        for page in ("lista.html", "detalle.html"):
            source = (ROOT / "convocatorias" / "templates" / "convocatorias" / page).read_text(encoding="utf-8")
            self.assertIn('{% extends "base.html" %}', source)
            self.assertNotIn("<html", source)

    def test_ruta_responsable_sin_script_ni_css_inline(self):
        source = (ROOT / "expedientes" / "templates" / "expedientes" / "ruta_responsable.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", source)
        self.assertNotIn('style="', source)
        self.assertIn("ruta_responsable.js", source)

    def test_mapa_carga_css_en_head_y_js_en_final(self):
        for page in ("detalle_expediente.html", "ruta_responsable.html"):
            source = (ROOT / "expedientes" / "templates" / "expedientes" / page).read_text(encoding="utf-8")
            self.assertIn("{% block extra_css %}", source)
            self.assertIn("{% block extra_js %}", source)
            self.assertIn("mapa_3d.css", source)

    def test_tema_unico_y_componentes_independientes(self):
        for path in (
            "core/static/css/tokens.css",
            "core/static/css/styles.css",
            "expedientes/static/expedientes/mapa_3d.css",
            "expedientes/static/expedientes/mapa_3d.js",
            "expedientes/static/expedientes/ruta_responsable.js",
        ):
            self.assertTrue((ROOT / path).is_file(), path)
        base = (ROOT / "core" / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertLess(base.index("css/tokens.css"), base.index("css/styles.css"))

    def test_navegacion_global_apunta_a_inicio(self):
        base = (ROOT / "core" / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertIn("{% url 'inicio' %}#convocatorias", base)
        self.assertIn("{% url 'inicio' %}#contacto", base)
