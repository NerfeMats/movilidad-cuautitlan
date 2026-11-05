"""Verificación del encabezado de destino en ruta del responsable."""
from django.test import SimpleTestCase
from django.template.loader import get_template


class DestinoRutaV193Tests(SimpleTestCase):
    def test_destino_visible_si_esta_asignado(self):
        fuente = get_template("expedientes/ruta_responsable.html").template.source
        self.assertIn("{% if expediente.ies_destino_id %}", fuente)
        self.assertIn("{{ expediente.ies_destino.ies.nombre }}", fuente)
        self.assertIn("{{ expediente.ies_destino.ies.pais }}", fuente)
        self.assertIn("Universidad de destino", fuente)

    def test_no_confunde_destino_con_aceptacion(self):
        fuente = get_template("expedientes/ruta_responsable.html").template.source
        self.assertIn("no acredita por sí sola una carta de aceptación", fuente)
        self.assertIn("Universidad de destino: aún no registrada", fuente)
