"""V20.4: pruebas de inventario de responsabilidades, sin modificar expedientes."""
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase
from django.template.loader import get_template
from unittest.mock import patch
from . import panel_responsable

class InventarioResponsabilidadesV204Tests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_interfaz_contiene_perspectivas_y_filtros(self):
        src = get_template('expedientes/centro_seguimiento.html').template.source
        self.assertIn('Pendientes actuales', src)
        self.assertIn('Inventario de responsabilidades', src)
        for nombre in ('responsable', 'etapa', 'estado', 'expediente'):
            self.assertIn('name="' + nombre + '"', src)
        self.assertIn('grupo.actividades', src)
        self.assertIn('grupos_inventario', src)
        self.assertIn('grupo.acciones', src)

    def test_usuario_anonimo_se_redirige(self):
        peticion = self.factory.get('/expedientes/responsable/seguimiento/?vista=inventario')
        peticion.user = AnonymousUser()
        respuesta = panel_responsable.centro_seguimiento(peticion)
        self.assertEqual(respuesta.status_code, 302)

    def test_personal_sin_permiso_recibe_denegacion(self):
        peticion = self.factory.get('/expedientes/responsable/seguimiento/?vista=inventario')
        class NoAutorizado:
            is_authenticated = True
            is_staff = True
            def has_perm(self, permiso): return False
        peticion.user = NoAutorizado()
        with self.assertRaises(PermissionDenied):
            panel_responsable.centro_seguimiento(peticion)

    def test_vista_pendientes_reutiliza_agrupacion_existente(self):
        peticion = self.factory.get('/expedientes/responsable/seguimiento/')
        class Autorizado:
            is_authenticated = True
            is_staff = True
            def has_perm(self, permiso): return permiso == 'expedientes.view_expedientemovilidad'
        peticion.user = Autorizado()
        with patch.object(panel_responsable, 'resumen_seguimiento', return_value={
            'actividades': [], 'acciones': [], 'borradores': 0, 'hoy': None,
        }), patch.object(panel_responsable, 'agrupar_pendientes', return_value=[]) as agrupar, patch.object(panel_responsable, 'render', return_value='ok') as render:
            respuesta = panel_responsable.centro_seguimiento(peticion)
        self.assertEqual(respuesta, 'ok')
        self.assertEqual(render.call_args.args[2]['vista'], 'pendientes')
        agrupar.assert_called_once_with([], [])
