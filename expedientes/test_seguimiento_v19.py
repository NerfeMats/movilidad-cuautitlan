"""Pruebas V19 con datos ficticios y almacenamiento temporal."""
from pathlib import Path
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from convocatorias.models import Convocatoria, TipoMovilidad
from .models import (ExpedienteMovilidad, ActividadProceso, ActividadExpediente,
                     AccionSeguimiento, HistorialAccion, HistorialExpediente, RecordatorioSeguimiento)
from .documentos_servicio import importar_documento_historico
from .seguimiento_servicio import vincular_documento


class SeguimientoV19Tests(TransactionTestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        config = override_settings(BASE_DIR=Path(tmp.name), MEDIA_ROOT=Path(tmp.name) / "media")
        config.enable()
        self.addCleanup(config.disable)
        U = get_user_model()
        self.alumno = U.objects.create_user(username="alumno_v19")
        self.otro = U.objects.create_user(username="otro_v19")
        self.staff = U.objects.create_superuser(username="staff_v19", password="test-only")
        tipo = TipoMovilidad.objects.create(nombre="V19 prueba")
        conv = Convocatoria.objects.create(tipo_movilidad=tipo, titulo="Prueba V19", ciclo="PRIMAVERA", anio=2027)
        self.exp = ExpedienteMovilidad.objects.create(alumno=self.alumno, convocatoria=conv)
        self.exp2 = ExpedienteMovilidad.objects.create(alumno=self.otro, convocatoria=conv)
        p = ActividadProceso.objects.create(tipo_movilidad=tipo, nombre="Entregar constancia", etapa="ANTES", responsable="ALUMNO", obligatorio=True, orden=1, estado_expediente="INICIADO")
        future = ActividadProceso.objects.create(tipo_movilidad=tipo, nombre="Actividad futura", etapa="DESPUES", responsable="DAAE", obligatorio=True, orden=2, estado_expediente="HOMOLOGACION")
        self.act = ActividadExpediente.objects.create(expediente=self.exp, actividad_proceso=p)
        ActividadExpediente.objects.create(expediente=self.exp, actividad_proceso=future)
        self.doc, _ = importar_documento_historico(usuario=self.staff, expediente=self.exp, archivo=SimpleUploadedFile("test.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"), nombre="Documento histórico ficticio")

    def test_centro_muestra_actual_sin_contar_futura(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("expedientes:centro_seguimiento"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entregar constancia")
        self.assertNotContains(response, "Actividad futura")

    def test_alumno_ve_solo_sus_pendientes(self):
        AccionSeguimiento.objects.create(expediente=self.exp, titulo="Acción visible", responsable="ALUMNO", visible_alumno=True)
        AccionSeguimiento.objects.create(expediente=self.exp, titulo="Interna restringida", responsable="DAAE")
        self.client.force_login(self.alumno)
        r = self.client.get(reverse("expedientes:mis_pendientes"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Acción visible")
        self.assertNotContains(r, "Interna restringida")
        self.assertNotContains(r, "Actividad futura")
        self.client.force_login(self.otro)
        r2 = self.client.get(reverse("expedientes:mis_pendientes"))
        self.assertNotContains(r2, "Acción visible")

    def test_tercero_no_accede_a_centro(self):
        self.client.force_login(self.alumno)
        with self.assertLogs("django.request", level="WARNING"):
            r = self.client.get(reverse("expedientes:centro_seguimiento"))
        self.assertEqual(r.status_code, 403)

    def test_vincular_no_completa_actividad_y_registra_historial(self):
        documento, cambio = vincular_documento(usuario=self.staff, documento_id=self.doc.pk, actividad_id=self.act.pk)
        self.assertTrue(cambio)
        self.assertEqual(documento.actividad_id, self.act.pk)
        self.act.refresh_from_db()
        self.assertEqual(self.act.estado, "PENDIENTE")
        self.assertIsNone(self.act.fecha_completada)
        self.assertEqual(documento.estado, "CARGADO")
        self.assertEqual(documento.visibilidad, "RESPONSABLE")
        self.assertEqual(HistorialExpediente.objects.filter(accion="DOCUMENTO_VINCULADO").count(), 1)
        _, otra = vincular_documento(usuario=self.staff, documento_id=self.doc.pk, actividad_id=self.act.pk)
        self.assertFalse(otra)
        self.assertEqual(HistorialExpediente.objects.filter(accion="DOCUMENTO_VINCULADO").count(), 1)
        _, cambio = vincular_documento(usuario=self.staff, documento_id=self.doc.pk)
        self.assertTrue(cambio)
        self.assertEqual(HistorialExpediente.objects.filter(accion="DOCUMENTO_DESVINCULADO").count(), 1)

    def test_vinculacion_cruzada_o_sin_permiso_se_rechaza(self):
        p = self.act.actividad_proceso
        act2 = ActividadExpediente.objects.create(expediente=self.exp2, actividad_proceso=p)
        with self.assertRaises(ValidationError):
            vincular_documento(usuario=self.staff, documento_id=self.doc.pk, actividad_id=act2.pk)
        with self.assertRaises(PermissionDenied):
            vincular_documento(usuario=self.alumno, documento_id=self.doc.pk, actividad_id=self.act.pk)

    def test_accion_administrativa_validaciones(self):
        accion = AccionSeguimiento(expediente=self.exp, actividad=self.act, titulo="Solicitar acuse", responsable="DAAE", estado="ESPERANDO_RESPUESTA")
        accion.save()
        self.assertIsNone(accion.fecha_limite)
        self.assertIsNone(accion.fecha_cierre)
        accion.visible_alumno = True
        with self.assertRaises(ValidationError):
            accion.save()
        accion.visible_alumno = False
        accion.estado = "COMPLETADA"
        with self.assertRaises(ValidationError):
            accion.save()
        accion.observaciones = "Acuse recibido y verificado"
        accion.save()
        self.assertIsNotNone(accion.fecha_cierre)

    def test_recordatorio_es_borrador_sin_envio(self):
        borrador = RecordatorioSeguimiento.objects.create(actividad=self.act, destinatario="Destinatario por verificar", asunto="Seguimiento", mensaje="Recordar entrega")
        self.assertEqual(borrador.estado, "BORRADOR")
        self.assertFalse(hasattr(borrador, "fecha_envio"))
        with self.assertRaises(ValidationError):
            RecordatorioSeguimiento(destinatario="x", asunto="x", mensaje="x").clean()
