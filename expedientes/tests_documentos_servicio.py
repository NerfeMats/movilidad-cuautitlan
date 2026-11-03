"""Fase 15A: pruebas aisladas de permisos y almacenamiento documental."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from convocatorias.models import Convocatoria, TipoMovilidad
from expedientes.models import ActividadExpediente, ActividadProceso, DocumentoExpediente, ExpedienteMovilidad, HistorialExpediente
from expedientes.documentos_servicio import (
    cargar_documento, documentos_de_actividad, abrir_documento, revisar_documento,
)


class DocumentosSegurosTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = override_settings(
            BASE_DIR=Path(self.tmp.name),
            MEDIA_ROOT=Path(self.tmp.name) / "media_publico",
        )
        self.config.enable()
        self.addCleanup(self.config.disable)
        tipo = TipoMovilidad.objects.create(nombre="Documental 15")
        convocatoria = Convocatoria.objects.create(
            tipo_movilidad=tipo, titulo="Convocatoria documental", ciclo="PRIMAVERA", anio=2027,
        )
        User = get_user_model()
        self.alumno = User.objects.create_user(username="doc15_alumno")
        self.ajeno = User.objects.create_user(username="doc15_ajeno")
        self.responsable = User.objects.create_user(username="doc15_resp", is_staff=True)
        for codigo in ("view_documentoexpediente", "add_documentoexpediente", "change_documentoexpediente"):
            self.responsable.user_permissions.add(Permission.objects.get(codename=codigo))
        self.e = ExpedienteMovilidad.objects.create(
            alumno=self.alumno, convocatoria=convocatoria, estado="EN_REVISION",
        )
        p = ActividadProceso.objects.create(
            tipo_movilidad=tipo, nombre="Adjuntar constancia", etapa="ANTES",
            responsable="ALUMNO", obligatorio=False, orden=1,
            estado_expediente="EN_REVISION", activo=True,
        )
        p2 = ActividadProceso.objects.create(
            tipo_movilidad=tipo, nombre="Validar constancia", etapa="ANTES",
            responsable="DAAE", obligatorio=False, orden=2,
            estado_expediente="EN_REVISION", activo=True,
        )
        self.a = ActividadExpediente.objects.create(expediente=self.e, actividad_proceso=p)
        self.a2 = ActividadExpediente.objects.create(expediente=self.e, actividad_proceso=p2)

    def pdf(self):
        return SimpleUploadedFile("constancia.pdf", b"%PDF-1.4\nDocumento de prueba", content_type="application/pdf")

    def cargar(self, usuario=None, actividad=None):
        return cargar_documento(
            usuario=usuario or self.alumno, actividad=actividad or self.a,
            archivo=self.pdf(), nombre="Constancia",
        )

    def test_01_alumno_carga_en_carpeta_fuera_media(self):
        doc = self.cargar()
        self.assertTrue(doc.archivo.name.startswith("privado/"))
        self.assertEqual(doc.estado, "CARGADO")
        self.assertTrue((Path(self.tmp.name) / "documentos_privados" / doc.archivo.name[8:]).is_file())
        self.assertFalse((Path(self.tmp.name) / "media_publico" / doc.archivo.name).exists())
        self.assertEqual(self.a.estado, "PENDIENTE")
        self.assertEqual(HistorialExpediente.objects.filter(accion="DOCUMENTO_CARGADO").count(), 1)

    def test_02_alumno_ajeno_no_puede_cargar(self):
        with self.assertRaises(PermissionDenied):
            self.cargar(usuario=self.ajeno)
        self.assertEqual(DocumentoExpediente.objects.count(), 0)

    def test_03_alumno_no_carga_actividad_del_organismo(self):
        with self.assertRaises(PermissionDenied):
            self.cargar(actividad=self.a2)

    def test_04_estacion_anterior_no_acepta_carga(self):
        self.e.estado = "ENVIADO_DAAE"
        self.e.save()
        with self.assertRaises(ValidationError):
            self.cargar()

    def test_05_no_acepta_archivo_de_extension_falsa(self):
        with self.assertRaises(ValidationError):
            cargar_documento(
                usuario=self.alumno, actividad=self.a, nombre="Falso",
                archivo=SimpleUploadedFile("malicioso.pdf", b"no es PDF"),
            )

    def test_06_no_acepta_archivo_demasiado_grande(self):
        with self.assertRaises(ValidationError):
            cargar_documento(
                usuario=self.alumno, actividad=self.a, nombre="Grande",
                archivo=SimpleUploadedFile("grande.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024)),
            )

    def test_07_alumno_puede_consultar_y_descargar_suyo(self):
        doc = self.cargar()
        self.assertEqual(documentos_de_actividad(usuario=self.alumno, actividad=self.a).count(), 1)
        with abrir_documento(usuario=self.alumno, documento=doc) as f:
            self.assertTrue(f.read().startswith(b"%PDF-"))

    def test_08_ajeno_no_consulta_ni_descarga(self):
        doc = self.cargar()
        with self.assertRaises(PermissionDenied):
            documentos_de_actividad(usuario=self.ajeno, actividad=self.a)
        with self.assertRaises(PermissionDenied):
            abrir_documento(usuario=self.ajeno, documento=doc)

    def test_09_alumno_no_aprueba(self):
        doc = self.cargar()
        with self.assertRaises(PermissionDenied):
            revisar_documento(usuario=self.alumno, documento=doc, aprobar=True, observaciones="")
        doc.refresh_from_db()
        self.assertEqual(doc.estado, "CARGADO")

    def test_10_responsable_aprueba_y_audita_sin_completar_actividad(self):
        doc = self.cargar()
        revisado = revisar_documento(usuario=self.responsable, documento=doc, aprobar=True, observaciones="Conforme")
        self.assertEqual(revisado.estado, "APROBADO")
        self.assertTrue(HistorialExpediente.objects.filter(accion="DOCUMENTO_APROBADO", usuario=self.responsable).exists())
        self.a.refresh_from_db()
        self.assertEqual(self.a.estado, "PENDIENTE")

    def test_11_rechazo_exige_observaciones(self):
        doc = self.cargar()
        with self.assertRaises(ValidationError):
            revisar_documento(usuario=self.responsable, documento=doc, aprobar=False, observaciones="")
        self.assertEqual(DocumentoExpediente.objects.get(pk=doc.pk).estado, "CARGADO")

    def test_12_responsable_rechaza_con_observaciones(self):
        doc = self.cargar()
        revisado = revisar_documento(usuario=self.responsable, documento=doc, aprobar=False, observaciones="Documento ilegible")
        self.assertEqual(revisado.estado, "REQUIERE_CORRECCION")
        self.assertEqual(revisado.observaciones, "Documento ilegible")

    def test_13_documento_preexistente_no_se_publica_automaticamente(self):
        doc = DocumentoExpediente.objects.create(
            expediente=self.e, actividad=self.a, nombre="Antiguo", archivo="movilidad/expedientes/antiguo.pdf",
        )
        with self.assertRaises(ValidationError):
            abrir_documento(usuario=self.alumno, documento=doc)

    def test_14_fallo_historial_revierte_registro_y_elimina_archivo(self):
        with patch.object(HistorialExpediente, "save", side_effect=RuntimeError("Fallo de auditoria")):
            with self.assertRaises(RuntimeError):
                self.cargar()
        self.assertEqual(DocumentoExpediente.objects.count(), 0)
        carpeta = Path(self.tmp.name) / "documentos_privados"
        self.assertEqual(list(carpeta.rglob("*.pdf")), [] if carpeta.exists() else [])

    def test_15_no_se_dictamina_dos_veces(self):
        doc = self.cargar()
        revisar_documento(usuario=self.responsable, documento=doc, aprobar=True, observaciones="Conforme")
        with self.assertRaises(ValidationError):
            revisar_documento(usuario=self.responsable, documento=doc, aprobar=False, observaciones="Otro")
