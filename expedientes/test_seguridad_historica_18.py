"""Pruebas HTTP integrales para documentos historicos reservados (v18).

No emplea expedientes ni documentos reales. El almacenamiento es temporal.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from convocatorias.models import Convocatoria, TipoMovilidad
from .documentos_servicio import importar_documento_historico
from .models import DocumentoExpediente, ExpedienteMovilidad, HistorialExpediente


class SeguridadHistoricaHTTPTests(TransactionTestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        configuracion = override_settings(
            BASE_DIR=Path(self.tmp.name),
            MEDIA_ROOT=Path(self.tmp.name) / "media",
        )
        configuracion.enable()
        self.addCleanup(configuracion.disable)

        tipo = TipoMovilidad.objects.create(nombre="Movilidad HTTP 18")
        convocatoria = Convocatoria.objects.create(
            tipo_movilidad=tipo,
            titulo="Registro interno ficticio HTTP 18",
            ciclo="PRIMAVERA",
            anio=2027,
        )
        usuarios = get_user_model()
        self.alumno = usuarios.objects.create_user(username="alumno_http_18")
        self.ajeno = usuarios.objects.create_user(username="ajeno_http_18")
        self.responsable = usuarios.objects.create_superuser(
            username="responsable_http_18", password="clave-solo-pruebas"
        )
        self.staff_sin_documentos = usuarios.objects.create_user(
            username="staff_limitado_http_18", is_staff=True
        )
        self.staff_sin_documentos.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="expedientes",
                codename="view_expedientemovilidad",
            )
        )
        self.expediente = ExpedienteMovilidad.objects.create(
            alumno=self.alumno,
            convocatoria=convocatoria,
            tipo_alta="EXCEPCIONAL",
            estado_inicial="EN_REVISION",
            estado="EN_REVISION",
            motivo_alta_excepcional=(
                "Expediente ficticio: fecha de recepci\u00f3n desconocida"
            ),
        )
        archivo = SimpleUploadedFile(
            "constancia_ficticia.pdf", b"%PDF-1.4\n%%EOF",
            content_type="application/pdf",
        )
        self.documento, creado = importar_documento_historico(
            usuario=self.responsable,
            expediente=self.expediente,
            archivo=archivo,
            nombre="Constancia historica ficticia",
            observaciones="Documento exclusivamente para pruebas",
        )
        self.assertTrue(creado)
        self.actividades_iniciales = self.expediente.actividades.count()
        self.url_descarga = reverse(
            "expedientes:documento_descargar", args=[self.documento.pk]
        )
        self.url_ruta = reverse(
            "expedientes:ruta_responsable", args=[self.expediente.pk]
        )

    def test_responsable_descarga_archivo_historico_por_http(self):
        self.client.force_login(self.responsable)
        respuesta = self.client.get(self.url_descarga)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Cache-Control"], "private, no-store")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment", respuesta["Content-Disposition"])
        try:
            contenido = b"".join(respuesta.streaming_content)
            self.assertTrue(contenido.startswith(b"%PDF-1.4"))
        finally:
            respuesta.close()

    def test_alumno_y_tercero_no_descargan_historico_reservado(self):
        for usuario in (self.alumno, self.ajeno):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                with self.assertLogs("django.request", level="WARNING"):
                    respuesta = self.client.get(self.url_descarga)
                self.assertEqual(respuesta.status_code, 403)

    def test_staff_sin_permiso_documental_no_descarga(self):
        self.client.force_login(self.staff_sin_documentos)
        with self.assertLogs("django.request", level="WARNING"):
            respuesta = self.client.get(self.url_descarga)
        self.assertEqual(respuesta.status_code, 403)

    def test_inventario_renderizado_y_sin_alterar_expediente(self):
        self.client.force_login(self.responsable)
        respuesta = self.client.get(self.url_ruta)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Inventario documental")
        self.assertContains(respuesta, self.url_descarga)
        self.assertEqual(
            DocumentoExpediente.objects.filter(expediente=self.expediente).count(), 1
        )
        self.assertEqual(
            DocumentoExpediente.objects.get(pk=self.documento.pk).actividad_id, None
        )
        self.expediente.refresh_from_db()
        self.assertEqual(self.expediente.estado, "EN_REVISION")
        self.assertEqual(self.expediente.actividades.count(), self.actividades_iniciales)
        self.assertEqual(
            HistorialExpediente.objects.filter(
                expediente=self.expediente, accion="DOCUMENTO_HISTORICO_IMPORTADO"
            ).count(), 1
        )

    def test_staff_sin_permiso_documental_no_ve_inventario(self):
        self.client.force_login(self.staff_sin_documentos)
        respuesta = self.client.get(self.url_ruta)
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, self.url_descarga)
        self.assertNotContains(respuesta, "Constancia historica ficticia")
