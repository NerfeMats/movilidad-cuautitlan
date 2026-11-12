"""Pruebas de la interfaz v21.1, aditivas y sin migraciones."""
from pathlib import Path
from types import SimpleNamespace
from django.test import SimpleTestCase
from django.template.loader import get_template
from .jornada_presentacion_v211 import construir_jornada

ROOT = Path(__file__).resolve().parent

class CentroGestionV211Tests(SimpleTestCase):
    def test_base_administrativa_separada(self):
        fuente = (ROOT / 'templates/expedientes/base_responsable.html').read_text(encoding='utf-8')
        self.assertIn('Mi jornada', fuente)
        self.assertIn('Estudiantes y movilidades', fuente)
        get_template('expedientes/base_responsable.html')

    def test_inicio_usa_areas_con_intencion(self):
        fuente = (ROOT / 'templates/expedientes/panel_responsable.html').read_text(encoding='utf-8')
        for texto in ('Pendientes a mi cargo', 'Actividades del alumno por supervisar', 'En espera de respuesta', 'Asuntos que requieren revisión'):
            self.assertIn(texto, fuente)
        get_template('expedientes/panel_responsable.html')

    def test_ruta_3d_no_se_pierde(self):
        fuente = (ROOT / 'templates/expedientes/ruta_responsable.html').read_text(encoding='utf-8')
        self.assertIn('id="ruta-responsable"', fuente)
        self.assertIn('Usted está aquí', fuente)
        self.assertIn('inventario_documental_responsable', fuente)
        self.assertNotIn('for documento in documentos_historicos', fuente)
        self.assertNotIn("{% url 'expedientes:documento_descargar' documento.pk %}", fuente)
        self.assertIn('documento_formulario.html', fuente)
        get_template('expedientes/ruta_responsable.html')

    def test_clasificacion_no_atribuye_todo_al_responsable(self):
        u = SimpleNamespace(pk=21)
        alumno = SimpleNamespace(responsable='ALUMNO')
        daae = SimpleNamespace(responsable='DAAE')
        actividades = [SimpleNamespace(actividad_proceso=alumno), SimpleNamespace(actividad_proceso=daae)]
        acciones = [
            SimpleNamespace(encargado_seguimiento_id=21, estado='PENDIENTE'),
            SimpleNamespace(encargado_seguimiento_id=22, estado='ESPERANDO_RESPUESTA'),
            SimpleNamespace(encargado_seguimiento_id=None, estado='REQUIERE_CORRECCION'),
        ]
        r = construir_jornada(actividades, acciones, u)
        self.assertEqual(len(r['gestiones']), 1)
        self.assertEqual(len(r['recordar']), 1)
        self.assertEqual(len(r['esperando']), 1)
        self.assertEqual(len(r['revision']), 1)

    def test_pestañas_sin_operaciones_de_escritura(self):
        fuente = (ROOT / 'static/expedientes/expediente_tabs_v211.js').read_text(encoding='utf-8')
        self.assertNotIn('fetch(', fuente)
        self.assertNotIn('XMLHttpRequest', fuente)
        self.assertIn('hashchange', fuente)
