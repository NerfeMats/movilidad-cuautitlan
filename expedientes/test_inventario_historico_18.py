"""Pruebas de control de acceso y alcance del inventario historico (v18)."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from . import panel_responsable as modulo
from .models import ExpedienteMovilidad


class InventarioHistoricoResponsableTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.expediente = SimpleNamespace(
            pk=7,
            estado=ExpedienteMovilidad.Estado.ENVIADO_DAAE,
            actividades=SimpleNamespace(all=lambda: []),
            puede_avanzar=lambda: False,
        )

    def usuario(self, documentos=True, expedientes=True, staff=True):
        permisos = set()
        if expedientes:
            permisos.add("expedientes.view_expedientemovilidad")
        if documentos:
            permisos.add("expedientes.view_documentoexpediente")
        return SimpleNamespace(
            is_authenticated=True,
            is_staff=staff,
            has_perm=lambda p: p in permisos,
        )

    def ejecutar(self, usuario):
        request = self.factory.get("/expedientes/responsable/7/")
        request.user = usuario
        fake_qs = Mock()
        fake_qs.order_by.return_value = ["doc-historico"]
        with (
            patch.object(modulo, "get_object_or_404", return_value=self.expediente),
            patch.object(modulo, "render", return_value=HttpResponse("ok")) as render,
            patch.object(modulo.DocumentoExpediente.objects, "filter", return_value=fake_qs) as filtro,
            patch.object(modulo.DocumentoExpediente.objects, "none", return_value=[]) as vacio,
        ):
            response = modulo.ruta_responsable(request, pk=7)
            return response, render.call_args.args[2], filtro, vacio

    def test_responsable_con_permiso_ve_solo_documentos_sin_actividad(self):
        response, contexto, filtro, vacio = self.ejecutar(self.usuario())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(contexto["puede_ver_documentos"])
        self.assertEqual(contexto["documentos_historicos"], ["doc-historico"])
        filtro.assert_called_once_with(expediente=self.expediente, actividad__isnull=True)
        vacio.assert_not_called()

    def test_responsable_sin_permiso_documental_no_recibe_documentos(self):
        response, contexto, filtro, vacio = self.ejecutar(self.usuario(documentos=False))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(contexto["puede_ver_documentos"])
        self.assertEqual(contexto["documentos_historicos"], [])
        filtro.assert_not_called()
        vacio.assert_called_once_with()

    def test_usuario_sin_permiso_expediente_es_rechazado(self):
        request = self.factory.get("/expedientes/responsable/7/")
        request.user = self.usuario(expedientes=False)
        with self.assertRaises(PermissionDenied):
            modulo.ruta_responsable(request, pk=7)

    def test_usuario_no_staff_es_rechazado(self):
        request = self.factory.get("/expedientes/responsable/7/")
        request.user = self.usuario(staff=False)
        with self.assertRaises(PermissionDenied):
            modulo.ruta_responsable(request, pk=7)
