"""Auditoría de comportamiento ACTUAL, no validación institucional de las reglas.

Se ejecuta solo contra la base de datos temporal creada por Django TestCase.
No altera modelos, migraciones ni registros existentes.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from convocatorias.models import Convocatoria, TipoMovilidad
from expedientes.models import (
    ActividadExpediente,
    ActividadProceso,
    ExpedienteMovilidad,
    HistorialExpediente,
)


class AuditoriaReglasActualesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = get_user_model()
        cls.alumno = usuario.objects.create_user(username="auditoria_alumno")
        cls.otro_alumno = usuario.objects.create_user(username="auditoria_otro")
        cls.responsable = usuario.objects.create_user(username="auditoria_responsable", is_staff=True)
        cls.tipo = TipoMovilidad.objects.create(nombre="Tipo auditoria de reglas")
        cls.convocatoria = Convocatoria.objects.create(
            tipo_movilidad=cls.tipo,
            titulo="Convocatoria auditoria",
            ciclo=Convocatoria.Ciclo.PRIMAVERA,
            anio=2027,
        )
        cls.expediente = ExpedienteMovilidad.objects.create(
            alumno=cls.alumno,
            convocatoria=cls.convocatoria,
            estado=ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE,
        )
        cls.otro_expediente = ExpedienteMovilidad.objects.create(
            alumno=cls.otro_alumno,
            convocatoria=cls.convocatoria,
            estado=ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE,
        )
        cls.catalogo = ActividadProceso.objects.create(
            tipo_movilidad=cls.tipo,
            nombre="Actividad auditada",
            etapa=ActividadProceso.Etapa.ANTES,
            responsable=ActividadProceso.Responsable.ALUMNO,
            obligatorio=True,
            orden=1,
            estado_expediente=ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE,
        )
        cls.actividad = ActividadExpediente.objects.create(
            expediente=cls.expediente,
            actividad_proceso=cls.catalogo,
            estado=ActividadExpediente.Estado.PENDIENTE,
        )
        cls.otra_actividad = ActividadExpediente.objects.create(
            expediente=cls.otro_expediente,
            actividad_proceso=cls.catalogo,
            estado=ActividadExpediente.Estado.PENDIENTE,
        )

    def test_01_estacion_sin_obligatorias_actualmente_permite_avanzar(self):
        """Riesgo conocido: la ausencia de requisitos no bloquea el avance."""
        self.catalogo.obligatorio = False
        self.catalogo.save(update_fields=["obligatorio"])
        self.assertTrue(self.expediente.puede_avanzar())

    def test_02_actividad_obligatoria_pendiente_bloquea(self):
        self.assertFalse(self.expediente.puede_avanzar())

    def test_03_completada_habilita_y_registra_fecha(self):
        self.actividad.estado = ActividadExpediente.Estado.COMPLETADA
        self.actividad.save()
        self.actividad.refresh_from_db()
        self.assertIsNotNone(self.actividad.fecha_completada)
        self.assertTrue(self.expediente.puede_avanzar())

    def test_04_no_aplica_sin_justificacion_actualmente_habilita(self):
        """Riesgo conocido: no hay control de motivo/autorización para NO_APLICA."""
        self.actividad.estado = ActividadExpediente.Estado.NO_APLICA
        self.actividad.observaciones = ""
        self.actividad.save()
        self.assertTrue(self.expediente.puede_avanzar())

    def test_05_catalogo_compartido_cambia_regla_en_dos_expedientes(self):
        """Riesgo conocido: la obligatoriedad no se congela por expediente."""
        self.assertFalse(self.expediente.puede_avanzar())
        self.assertFalse(self.otro_expediente.puede_avanzar())
        self.catalogo.obligatorio = False
        self.catalogo.save(update_fields=["obligatorio"])
        self.assertTrue(self.expediente.puede_avanzar())
        self.assertTrue(self.otro_expediente.puede_avanzar())

    def test_06_avance_registra_usuario_y_transicion(self):
        self.actividad.estado = ActividadExpediente.Estado.COMPLETADA
        self.actividad.save()
        self.assertTrue(self.expediente.avanzar_estado(usuario=self.responsable))
        self.expediente.refresh_from_db()
        self.assertEqual(self.expediente.estado, ExpedienteMovilidad.Estado.EN_REVISION)
        historial = HistorialExpediente.objects.get(expediente=self.expediente)
        self.assertEqual(historial.usuario_id, self.responsable.pk)
        self.assertEqual(historial.estado_anterior, ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE)
        self.assertEqual(historial.estado_nuevo, ExpedienteMovilidad.Estado.EN_REVISION)

    def test_07_fallo_historial_no_revierte_cambio_sin_transaccion_explicita(self):
        """Caracteriza riesgo: el save de expediente precede al create de historial.

        Usamos una excepción artificial y un savepoint controlado para observar
        el estado en esta prueba, sin contaminar el resto de la suite.
        """
        self.actividad.estado = ActividadExpediente.Estado.COMPLETADA
        self.actividad.save()
        with patch.object(HistorialExpediente.objects, "create", side_effect=RuntimeError("Fallo simulado del historial")):
            with self.assertRaisesRegex(RuntimeError, "Fallo simulado"):
                self.expediente.avanzar_estado(usuario=self.responsable)
        self.expediente.refresh_from_db()
        self.assertEqual(self.expediente.estado, ExpedienteMovilidad.Estado.EN_REVISION)
        self.assertFalse(HistorialExpediente.objects.filter(expediente=self.expediente).exists())

    def test_08_estado_terminal_no_puede_avanzar(self):
        self.expediente.estado = ExpedienteMovilidad.Estado.CERRADO
        self.expediente.save()
        self.assertFalse(self.expediente.puede_avanzar())
        self.assertFalse(self.expediente.avanzar_estado(usuario=self.responsable))
