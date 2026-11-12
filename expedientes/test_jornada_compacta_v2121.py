from pathlib import Path
from django.test import SimpleTestCase
from django.template.loader import get_template

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "templates/expedientes/panel_responsable.html"

class JornadaCompactaV2121Tests(SimpleTestCase):
    def test_plantilla_compila(self):
        get_template("expedientes/panel_responsable.html")

    def test_no_duplica_tabla_de_estudiantes(self):
        src = HTML.read_text(encoding="utf-8")
        self.assertNotIn('id="estudiantes"', src)
        self.assertNotIn('for e in expedientes', src)
        self.assertNotIn('class="cg-metrics"', src)

    def test_muestra_maximo_dos_de_cada_clase(self):
        src = HTML.read_text(encoding="utf-8")
        for clase in ('gestiones', 'recordar', 'esperando', 'revision'):
            self.assertIn('jornada.' + clase + '|slice:":2"', src)

    def test_oculta_categorias_vacias(self):
        src = HTML.read_text(encoding="utf-8")
        for clase in ('gestiones', 'recordar', 'esperando', 'revision'):
            self.assertIn('{% if jornada.' + clase + ' %}', src)

    def test_rutas_existentes_se_conservan(self):
        src = HTML.read_text(encoding="utf-8")
        self.assertIn("'expedientes:centro_seguimiento'", src)
        self.assertIn("'expedientes:ruta_responsable'", src)
        self.assertNotIn('documento_descargar', src)

    def test_estructura_critica_y_sin_textos_obvios(self):
        src = HTML.read_text(encoding="utf-8")
        self.assertIn('display:grid', src)
        self.assertIn('class="j-task"', src)
        self.assertNotIn('Las cifras representan', src)
        self.assertNotIn('Vista breve.', src)
        self.assertNotIn('no confirma el envío', src)
