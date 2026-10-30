"""Pruebas de regresión del mapa y los permisos, sin cambiar reglas de negocio."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from convocatorias.models import TipoMovilidad, Convocatoria
from .models import ExpedienteMovilidad, ActividadProceso, ActividadExpediente


class MapaMovilidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alumno = User.objects.create_user(username="alumno_mapa", password="ClavePrueba1!")
        cls.otro = User.objects.create_user(username="otro_mapa", password="ClavePrueba1!")
        cls.staff = User.objects.create_user(username="responsable_mapa", password="ClavePrueba1!", is_staff=True)
        cls.tipo = TipoMovilidad.objects.create(nombre="Tipo de prueba")
        cls.convocatoria = Convocatoria.objects.create(
            tipo_movilidad=cls.tipo, titulo="Convocatoria prueba", ciclo="PRIMAVERA", anio=2027,
        )
        cls.actividad_catalogo = ActividadProceso.objects.create(
            tipo_movilidad=cls.tipo, nombre="Reunir documentos", etapa="ANTES",
            responsable="ALUMNO", obligatorio=True, orden=1,
            estado_expediente=ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE,
        )
        cls.exp = ExpedienteMovilidad.objects.create(alumno=cls.alumno, convocatoria=cls.convocatoria)
        cls.act = ActividadExpediente.objects.create(
            expediente=cls.exp, actividad_proceso=cls.actividad_catalogo,
            estado=ActividadExpediente.Estado.PENDIENTE,
        )

    def test_nueve_estaciones_en_vista_alumno(self):
        self.client.force_login(self.alumno)
        r = self.client.get(reverse("expedientes:detalle", args=[self.exp.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["estaciones"]), 9)
        self.assertContains(r, "mapa-movilidad")
        self.assertContains(r, "Reunir documentos")

    def test_alumno_no_consulta_expediente_ajeno(self):
        self.client.force_login(self.otro)
        r = self.client.get(reverse("expedientes:detalle", args=[self.exp.pk]))
        self.assertEqual(r.status_code, 404)

    def test_staff_sin_permiso_no_accede_al_panel(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse("expedientes:panel_responsable"))
        self.assertNotEqual(r.status_code, 200)

    def test_staff_con_permiso_accede_al_panel_y_ruta(self):
        permiso = Permission.objects.get(codename="view_expedientemovilidad")
        self.staff.user_permissions.add(permiso)
        self.client.force_login(self.staff)
        panel = self.client.get(reverse("expedientes:panel_responsable"))
        ruta = self.client.get(reverse("expedientes:ruta_responsable", args=[self.exp.pk]))
        self.assertEqual(panel.status_code, 200)
        self.assertEqual(ruta.status_code, 200)
        self.assertContains(ruta, "Usted está aquí")
        self.assertEqual(len(ruta.context["estaciones"]), 9)

    def test_pendiente_bloquea_y_completada_permite_en_su_etapa(self):
        self.exp.estado = ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE
        self.exp.save()
        self.assertFalse(self.exp.puede_avanzar())
        self.act.estado = ActividadExpediente.Estado.COMPLETADA
        self.act.save()
        self.assertTrue(self.exp.puede_avanzar())
        self.assertIsNotNone(self.act.fecha_completada)

    def test_no_registrada_no_es_completada(self):
        self.exp.estado = ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE
        self.exp.save()
        self.act.estado = ActividadExpediente.Estado.NO_REGISTRADA
        self.act.save()
        self.assertFalse(self.exp.puede_avanzar())

    def test_cancelado_no_se_presenta_como_estacion_final(self):
        self.exp.estado = ExpedienteMovilidad.Estado.CANCELADO
        self.exp.save()
        permiso = Permission.objects.get(codename="view_expedientemovilidad")
        self.staff.user_permissions.add(permiso)
        self.client.force_login(self.staff)
        r = self.client.get(reverse("expedientes:ruta_responsable", args=[self.exp.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Expediente cancelado")
        self.assertEqual(len(r.context["estaciones"]), 9)

    def test_alumno_muestra_actividad_obligatoria_y_contexto_de_etapa(self):
        self.client.force_login(self.alumno)
        r = self.client.get(reverse("expedientes:detalle", args=[self.exp.pk]))
        self.assertContains(r, 'id="mov3d-stage-context"')
        self.assertContains(r, 'data-situacion="futura"')
        self.assertContains(r, "Obligatoria: Sí")
        self.assertContains(r, "Esto no acredita que se hayan completado")
        self.assertContains(r, "Estado real:")

    def test_responsable_detalla_actividad_y_aclara_bloqueo_de_etapa_actual(self):
        self.exp.estado = ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE
        self.exp.save()
        permiso = Permission.objects.get(codename="view_expedientemovilidad")
        self.staff.user_permissions.add(permiso)
        self.client.force_login(self.staff)
        r = self.client.get(reverse("expedientes:ruta_responsable", args=[self.exp.pk]))
        self.assertContains(r, "Reunir documentos")
        self.assertContains(r, "Obligatoria: Sí")
        self.assertContains(r, "Condición de la etapa actual")
        self.assertContains(r, "Este mensaje no se refiere necesariamente a la estación consultada")

    def test_actividad_futura_completada_no_habilita_salto_de_etapa(self):
        futura = ActividadProceso.objects.create(
            tipo_movilidad=self.tipo, nombre="Preparar salida", etapa="ANTES",
            responsable="ALUMNO", obligatorio=True, orden=2,
            estado_expediente=ExpedienteMovilidad.Estado.PREPARACION_MOVILIDAD,
        )
        ActividadExpediente.objects.create(
            expediente=self.exp, actividad_proceso=futura,
            estado=ActividadExpediente.Estado.COMPLETADA,
        )
        self.exp.estado = ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE
        self.exp.save()
        self.assertFalse(self.exp.puede_avanzar())
        self.assertEqual(self.exp.SIGUIENTE_ESTADO[self.exp.estado], ExpedienteMovilidad.Estado.EN_REVISION)
