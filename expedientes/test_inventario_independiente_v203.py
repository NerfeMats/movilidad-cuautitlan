"""V20.3: inventario fuera de estaciones, con permisos de acceso."""
from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase, RequestFactory
from django.template.loader import get_template
from django.urls import resolve, reverse
from . import panel_responsable


class InventarioIndependienteV203Tests(SimpleTestCase):
    def test_ruta_no_contiene_tabla_de_inventario(self):
        fuente = get_template("expedientes/ruta_responsable.html").template.source
        self.assertNotIn('for documento in documentos_historicos', fuente)
        self.assertNotIn('for documento in documentos_vinculados', fuente)
        self.assertIn("expedientes:inventario_documental_responsable", fuente)
        self.assertIn("Expediente documental de la actividad", fuente)

    def test_inventario_nueva_plantilla_con_controles_existentes(self):
        fuente = get_template("expedientes/inventario_documental.html").template.source
        self.assertEqual(fuente.count("Inventario documental histórico"), 1)
        self.assertIn('expedientes:documento_descargar', fuente)
        self.assertIn('expedientes:documento_vincular', fuente)
        self.assertIn('perms.expedientes.change_documentoexpediente', fuente)
        self.assertNotIn("hist?rico", fuente)

    def test_url_documental_es_una_vista_distinta(self):
        ruta = reverse("expedientes:inventario_documental_responsable", args=[8])
        self.assertEqual(ruta, "/expedientes/responsable/8/documentos/")
        self.assertEqual(resolve(ruta).func, panel_responsable.inventario_documental_responsable)

    def test_usuario_anonimo_no_entra(self):
        peticion = RequestFactory().get("/expedientes/responsable/8/documentos/")
        peticion.user = AnonymousUser()
        respuesta = panel_responsable.inventario_documental_responsable(peticion, 8)
        self.assertEqual(respuesta.status_code, 302)

    def test_sin_permiso_de_responsable_se_rechaza(self):
        peticion = RequestFactory().get("/expedientes/responsable/8/documentos/")
        class Usuario:
            is_authenticated = True
            is_staff = True
            def has_perm(self, permiso):
                return permiso == "expedientes.view_documentoexpediente"
        peticion.user = Usuario()
        with self.assertRaises(PermissionDenied):
            panel_responsable.inventario_documental_responsable(peticion, 8)

    def test_sin_permiso_documental_se_rechaza(self):
        peticion = RequestFactory().get("/expedientes/responsable/8/documentos/")
        class Usuario:
            is_authenticated = True
            is_staff = True
            def has_perm(self, permiso):
                return permiso == "expedientes.view_expedientemovilidad"
        peticion.user = Usuario()
        with self.assertRaises(PermissionDenied):
            panel_responsable.inventario_documental_responsable(peticion, 8)
