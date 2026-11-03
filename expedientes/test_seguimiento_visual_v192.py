"""Comprobación de presentación de seguimiento sin alterar estados."""
from django.test import SimpleTestCase
from django.template.loader import get_template

class SeguimientoVisualV192Tests(SimpleTestCase):
    def test_ruta_muestra_seguimientos_ligados_a_actividad(self):
        plantilla = get_template("expedientes/ruta_responsable.html")
        origen = plantilla.template.source
        self.assertIn("a.acciones_seguimiento.all", origen)
        self.assertIn("seguimiento.descripcion", origen)
        self.assertIn("seguimiento.get_estado_display", origen)
        self.assertIn("no acredita por sí sola", origen)
        self.assertNotIn("actividad.estado =", origen)
