from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.template.loader import get_template
from .models import UniversidadCandidataExpediente


class CandidaturasV20Tests(SimpleTestCase):
    def test_estado_por_defecto_no_es_aceptacion(self):
        obj = UniversidadCandidataExpediente()
        self.assertEqual(obj.estado, "PROPUESTA")

    def test_aceptacion_requiere_referencia_de_evidencia(self):
        obj = UniversidadCandidataExpediente(estado="ACEPTADA")
        with self.assertRaises(ValidationError):
            obj.clean()

    def test_postulacion_requiere_referencia_de_evidencia(self):
        obj = UniversidadCandidataExpediente(estado="POSTULADA")
        with self.assertRaises(ValidationError):
            obj.clean()

    def test_propuesta_sin_aceptacion_es_valida(self):
        obj = UniversidadCandidataExpediente(estado="PROPUESTA")
        obj.clean()

    def test_template_no_confunde_candidata_con_destino(self):
        fuente = get_template("expedientes/ruta_responsable.html").template.source
        self.assertIn("Universidades candidatas", fuente)
        self.assertIn("alternativa.get_estado_display", fuente)
        self.assertIn("No acreditan por sí solas", fuente)
