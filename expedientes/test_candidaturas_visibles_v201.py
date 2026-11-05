"""Pruebas de la tarjeta condicional de candidaturas (V20.1)."""
from types import SimpleNamespace
from django.template import Context, Template
from django.template.loader import get_template
from django.test import SimpleTestCase


class CandidaturasVisiblesV201Tests(SimpleTestCase):
    @staticmethod
    def _fragmento():
        fuente = get_template("expedientes/ruta_responsable.html").template.source
        inicio = fuente.index("{% with candidatas=expediente.universidades_candidatas.all %}")
        fin = fuente.index("{% endwith %}", inicio) + len("{% endwith %}")
        return Template(fuente[inicio:fin])

    def test_sin_candidaturas_no_aparece_tarjeta(self):
        exp = SimpleNamespace(universidades_candidatas=SimpleNamespace(all=lambda: []))
        html = self._fragmento().render(Context({"expediente": exp}))
        self.assertNotIn("Universidades candidatas", html)
        self.assertNotIn("No hay universidades candidatas registradas", html)

    def test_con_candidaturas_aparece_tarjeta_y_estado(self):
        candidata = SimpleNamespace(
            ies=SimpleNamespace(nombre="Universidad de Chile", pais="Chile"),
            get_estado_display=lambda: "Propuesta", observaciones="",
        )
        exp = SimpleNamespace(universidades_candidatas=SimpleNamespace(all=lambda: [candidata]))
        html = self._fragmento().render(Context({"expediente": exp}))
        self.assertIn("Universidades candidatas", html)
        self.assertIn("Universidad de Chile", html)
        self.assertIn("Propuesta", html)
