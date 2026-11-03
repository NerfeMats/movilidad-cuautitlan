"""Regresión 15C: clasificación, plantillas y nombre de archivo original."""
from types import SimpleNamespace
from django.test import SimpleTestCase
from django.template.loader import get_template
from .templatetags.documentos_presentacion import (
    documentos_aprobados, documentos_pendientes, documentos_correccion,
)

class PresentacionDocumentosTests(SimpleTestCase):
    def test_agrupacion_de_estados_sin_alterar_datos(self):
        docs = [SimpleNamespace(estado=e) for e in (
            "CARGADO", "APROBADO", "REQUIERE_CORRECCION", "EN_REVISION", "RECHAZADO")]
        self.assertEqual(len(documentos_aprobados(docs)), 1)
        self.assertEqual(len(documentos_pendientes(docs)), 2)
        self.assertEqual(len(documentos_correccion(docs)), 2)
        self.assertEqual(len(docs), 5)

    def test_agrupacion_vacia(self):
        self.assertFalse(documentos_aprobados([]))
        self.assertFalse(documentos_pendientes([]))
        self.assertFalse(documentos_correccion([]))

    def test_plantillas_compilan(self):
        for nombre in (
            "detalle_expediente.html", "ruta_responsable.html",
            "_documentos_secciones.html", "_documento_tarjeta.html",
            "_documento_formulario.html",
        ):
            get_template("expedientes/" + nombre)

    def test_referencias_visuales_a_estado_y_archivo(self):
        from pathlib import Path
        source = (Path(__file__).parent / "templates/expedientes/_documento_tarjeta.html").read_text(encoding="utf-8")
        self.assertIn("documento.nombre_archivo_original", source)
        self.assertIn("doc-panel__status", source)
        self.assertIn("documento.get_estado_display", source)

    def test_formulario_plegable_y_actividad_completada(self):
        from pathlib import Path
        source = (Path(__file__).parent / "templates/expedientes/_documento_formulario.html").read_text(encoding="utf-8")
        self.assertIn("<details", source)
        self.assertIn("actividad.estado != 'COMPLETADA'", source)
        self.assertIn("Adjuntar otro documento", source)
