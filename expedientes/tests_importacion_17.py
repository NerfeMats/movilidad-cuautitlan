"""Pruebas de seguridad y alta histórica; no usa datos personales reales."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from convocatorias.models import Convocatoria, TipoMovilidad
from expedientes.admin import DocumentoExpedienteAdmin
from expedientes.documentos_servicio import importar_documento_historico, abrir_documento
from expedientes.models import DocumentoExpediente, ExpedienteMovilidad, HistorialExpediente


class ImportacionHistorica17Tests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = override_settings(
            BASE_DIR=Path(self.tmp.name), MEDIA_ROOT=Path(self.tmp.name) / "media"
        )
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.tipo = TipoMovilidad.objects.create(nombre="Movilidad 17")
        self.conv = Convocatoria.objects.create(
            tipo_movilidad=self.tipo, titulo="Interna de pruebas 17",
            ciclo="PRIMAVERA", anio=2027,
        )
        U = get_user_model()
        self.alumno = U.objects.create_user(username="alumno_17")
        self.responsable = U.objects.create_superuser(username="responsable_17", password="temporal")
        self.exp = ExpedienteMovilidad.objects.create(
            alumno=self.alumno, convocatoria=self.conv,
            tipo_alta="EXCEPCIONAL", estado_inicial="EN_REVISION", estado="EN_REVISION",
            motivo_alta_excepcional="Expediente heredado, fecha de recepción desconocida",
        )

    def pdf(self):
        return SimpleUploadedFile("prueba.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf")

    def test_fecha_desconocida_explicitada(self):
        self.assertIsNone(self.exp.fecha_recepcion_area)
        self.exp.full_clean()

    def test_fecha_desconocida_sin_justificacion_es_invalida(self):
        self.exp.motivo_alta_excepcional = "Expediente heredado"
        with self.assertRaises(ValidationError):
            self.exp.full_clean()

    def test_importacion_restringida_y_sin_cambiar_etapa(self):
        doc, creado = importar_documento_historico(
            usuario=self.responsable, expediente=self.exp, archivo=self.pdf(),
            nombre="Documento de prueba", observaciones="Origen físico",
        )
        self.assertTrue(creado)
        self.assertIsNone(doc.actividad_id)
        self.assertEqual(doc.visibilidad, "RESPONSABLE")
        self.assertEqual(doc.estado, "CARGADO")
        self.assertEqual(ExpedienteMovilidad.objects.get(pk=self.exp.pk).estado, "EN_REVISION")
        self.assertTrue(HistorialExpediente.objects.filter(
            expediente=self.exp, accion="DOCUMENTO_HISTORICO_IMPORTADO").exists())
        with self.assertRaises(PermissionDenied):
            abrir_documento(usuario=self.alumno, documento=doc)
        with abrir_documento(usuario=self.responsable, documento=doc) as f:
            self.assertTrue(f.read().startswith(b"%PDF-"))

    def test_documento_duplicado_se_omite(self):
        uno, creado1 = importar_documento_historico(
            usuario=self.responsable, expediente=self.exp, archivo=self.pdf(), nombre="Prueba"
        )
        dos, creado2 = importar_documento_historico(
            usuario=self.responsable, expediente=self.exp, archivo=self.pdf(), nombre="Otra copia"
        )
        self.assertTrue(creado1)
        self.assertFalse(creado2)
        self.assertEqual(uno.pk, dos.pk)
        self.assertEqual(DocumentoExpediente.objects.filter(expediente=self.exp).count(), 1)

    def test_alumno_no_importa_historicos(self):
        with self.assertRaises(PermissionDenied):
            importar_documento_historico(
                usuario=self.alumno, expediente=self.exp, archivo=self.pdf(), nombre="No autorizado"
            )

    def test_admin_no_permite_cambios_directos(self):
        panel = DocumentoExpedienteAdmin(DocumentoExpediente, admin.site)
        self.assertFalse(panel.has_add_permission(Mock()))
        self.assertFalse(panel.has_change_permission(Mock()))
        self.assertFalse(panel.has_delete_permission(Mock()))
        self.assertIn("archivo", panel.exclude)
