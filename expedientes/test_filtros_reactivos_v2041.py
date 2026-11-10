from pathlib import Path
from django.test import SimpleTestCase


class FiltrosAutomaticosInventarioTests(SimpleTestCase):

    def test_cuatro_selectores_envian_formulario_al_cambiar(self):
        archivo = (
            Path(__file__).resolve().parent
            / "templates"
            / "expedientes"
            / "centro_seguimiento.html"
        )

        html = archivo.read_text(encoding="utf-8")

        for identificador in (
            "fil-responsable",
            "fil-etapa",
            "fil-estado",
            "fil-expediente",
        ):
            self.assertIn(f'id="{identificador}"', html)

        self.assertEqual(
            html.count('onchange="this.form.requestSubmit()"'),
            5,
        )

    def test_se_conserva_envio_sin_javascript(self):
        archivo = (
            Path(__file__).resolve().parent
            / "templates"
            / "expedientes"
            / "centro_seguimiento.html"
        )

        html = archivo.read_text(encoding="utf-8")

        self.assertIn("<noscript>", html)
        self.assertIn('type="submit"', html)
