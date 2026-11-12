"""Contratos de interfaz v21.2.3: sin cambios de base de datos."""
from pathlib import Path
from django.test import SimpleTestCase
from django.template.loader import get_template

ROOT = Path(__file__).resolve().parent
SEGUIMIENTO = ROOT / 'templates' / 'expedientes' / 'centro_seguimiento.html'
JORNADA = ROOT / 'templates' / 'expedientes' / 'panel_responsable.html'
CSS = ROOT / 'static' / 'expedientes' / 'seguimiento_v2123.css'


class SeguimientoJornadaV2123Tests(SimpleTestCase):
    def test_plantillas_compilan(self):
        get_template('expedientes/centro_seguimiento.html')
        get_template('expedientes/panel_responsable.html')

    def test_tres_pestanas_con_rutas_originales(self):
        html = SEGUIMIENTO.read_text(encoding='utf-8')
        self.assertIn('class="cg-follow-tabs"', html)
        self.assertEqual(html.count('class="cg-follow-tab {%'), 3)
        self.assertIn('?vista=inventario', html)
        self.assertIn('?vista=reglas', html)
        self.assertIn("'expedientes:centro_seguimiento'", html)
        self.assertIn('aria-current="page"', html)

    def test_acciones_separadas_con_ayudas_accesibles(self):
        html = SEGUIMIENTO.read_text(encoding='utf-8')
        self.assertIn('Registrar gestión', html)
        self.assertIn('Preparar recordatorio', html)
        self.assertIn("'admin:expedientes_accionseguimiento_add'", html)
        self.assertIn("'admin:expedientes_recordatorioseguimiento_add'", html)
        self.assertEqual(html.count('class="cg-help-trigger"'), 2)
        self.assertEqual(html.count('class="cg-help-trigger" data-bs-toggle="tooltip"'), 2)
        self.assertIn('No cambia su etapa', html)
        self.assertIn('no envía mensajes automáticamente', html)
        self.assertIn('data-bs-trigger="hover focus click"', html)

    def test_filtros_existentes_y_diagnostico_siguen_presentes(self):
        html = SEGUIMIENTO.read_text(encoding='utf-8')
        self.assertEqual(html.count('onchange="this.form.requestSubmit()"'), 5)
        for identifier in ('fil-responsable','fil-etapa','fil-estado','fil-expediente','expediente-reglas'):
            self.assertIn('id="' + identifier + '"', html)
        self.assertIn('Diagnóstico consultivo de reglas', html)
        self.assertIn('No se encontró un expediente activo', html)
        self.assertIn('no autoriza avances', html)

    def test_jornada_sin_contadores_sueltos_y_cantidades_contextuales(self):
        html = JORNADA.read_text(encoding='utf-8')
        self.assertNotIn('class="j-counts"', html)
        self.assertNotIn('Debo recordar / supervisar', html)
        self.assertNotIn('Mis gestiones', html)
        for categoria in ('gestiones','recordar','esperando','revision'):
            self.assertIn('jornada.' + categoria + '|length', html)
            self.assertIn('jornada.' + categoria + '|slice:":2"', html)
        self.assertIn('Pendientes a mi cargo', html)
        self.assertIn('Actividades del alumno por supervisar', html)
        self.assertIn("'expedientes:ruta_responsable'", html)
        self.assertNotIn('documento_descargar', html)

    def test_estilos_propios_sin_cambiar_tema_publico(self):
        html = SEGUIMIENTO.read_text(encoding='utf-8')
        self.assertIn("'expedientes/seguimiento_v2123.css'", html)
        css = CSS.read_text(encoding='utf-8')
        self.assertIn('.cg-body .cg-follow-tabs', css)
        self.assertIn('.cg-body .cg-follow-head', css)
        self.assertIn('focus-visible', css)
        self.assertIn('#4c5f59', css)
