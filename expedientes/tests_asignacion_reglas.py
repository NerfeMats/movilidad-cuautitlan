"""Fase 2.1: asignacion explicita, sin cambiar puede_avanzar()."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from convocatorias.models import Convocatoria, TipoMovilidad
from expedientes.asignacion_reglas import asignar_reglas_expediente
from expedientes.models import (
    ActividadProceso,
    ExpedienteMovilidad,
    EstadoConfiguracion,
    PoliticaRegla,
    ReglaActividadConvocatoria,
    ReglaActividadExpediente,
)


class AsignacionReglasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tipo = TipoMovilidad.objects.create(nombre="Asignacion reglas 13")
        cls.conv = Convocatoria.objects.create(
            tipo_movilidad=cls.tipo, titulo="Convocatoria de pruebas 13",
            ciclo="PRIMAVERA", anio=2027,
        )
        cls.alumno = get_user_model().objects.create_user(username="alumno_fase13")
        cls.expediente = ExpedienteMovilidad.objects.create(
            alumno=cls.alumno, convocatoria=cls.conv,
            estado=ExpedienteMovilidad.Estado.INICIADO,
        )
        cls.catalogo1 = ActividadProceso.objects.create(
            tipo_movilidad=cls.tipo, nombre="Actividad primera 13",
            etapa="ANTES", responsable="ALUMNO", obligatorio=True,
            estado_expediente=ExpedienteMovilidad.Estado.INICIADO,
            activo=True, orden=1,
        )
        cls.catalogo2 = ActividadProceso.objects.create(
            tipo_movilidad=cls.tipo, nombre="Actividad segunda 13",
            etapa="ANTES", responsable="DAAE", obligatorio=False,
            estado_expediente=ExpedienteMovilidad.Estado.EN_REVISION,
            activo=True, orden=2,
        )

    def configurar(self, proceso, politica=PoliticaRegla.BLOQUEANTE):
        return ReglaActividadConvocatoria.objects.create(
            convocatoria=self.conv, actividad_proceso=proceso,
            politica=politica, estado_configuracion=EstadoConfiguracion.DEFINIDA,
            fundamento="Criterio provisional de prueba, no regla institucional",
        )

    def test_01_alta_tradicional_no_asigna_reglas(self):
        self.expediente.crear_actividades_iniciales()
        self.assertEqual(self.expediente.actividades.count(), 2)
        self.assertEqual(ReglaActividadExpediente.objects.count(), 0)

    def test_02_sin_reglas_definidas_rechaza_y_revierte_alta_optativa(self):
        with self.assertRaises(ValidationError):
            self.expediente.crear_actividades_iniciales(asignar_reglas=True)
        self.assertEqual(self.expediente.actividades.count(), 0)
        self.assertEqual(ReglaActividadExpediente.objects.count(), 0)

    def test_03_configuracion_parcial_no_deja_copias_ni_actividades(self):
        self.configurar(self.catalogo1)
        with self.assertRaises(ValidationError):
            self.expediente.crear_actividades_iniciales(asignar_reglas=True)
        self.assertEqual(self.expediente.actividades.count(), 0)
        self.assertEqual(ReglaActividadExpediente.objects.count(), 0)

    def test_04_acepta_configuracion_completa(self):
        self.configurar(self.catalogo1)
        self.configurar(self.catalogo2, PoliticaRegla.SEGUIMIENTO)
        self.expediente.crear_actividades_iniciales(asignar_reglas=True)
        self.assertEqual(self.expediente.actividades.count(), 2)
        self.assertEqual(ReglaActividadExpediente.objects.count(), 2)

    def test_05_reintento_idempotente(self):
        self.configurar(self.catalogo1)
        self.configurar(self.catalogo2)
        self.expediente.crear_actividades_iniciales(asignar_reglas=True)
        self.expediente.crear_actividades_iniciales(asignar_reglas=True)
        self.assertEqual(ReglaActividadExpediente.objects.count(), 2)
        self.assertEqual(self.expediente.actividades.count(), 2)

    def test_06_copia_no_cambia_tras_editar_regla_origen(self):
        regla = self.configurar(self.catalogo1)
        self.configurar(self.catalogo2)
        self.expediente.crear_actividades_iniciales(asignar_reglas=True)
        copia = ReglaActividadExpediente.objects.get(regla_origen=regla)
        regla.politica = PoliticaRegla.SEGUIMIENTO
        regla.save(update_fields=["politica"])
        copia.refresh_from_db()
        self.assertEqual(copia.politica, PoliticaRegla.BLOQUEANTE)

    def test_07_asignar_no_altera_regla_vigente_de_avance(self):
        self.configurar(self.catalogo1, PoliticaRegla.SEGUIMIENTO)
        self.configurar(self.catalogo2, PoliticaRegla.BLOQUEANTE)
        self.expediente.crear_actividades_iniciales(asignar_reglas=True)
        # La actividad 1 continua siendo obligatoria segun el catalogo
        # actual; la nueva copia NO interviene en puede_avanzar().
        self.assertFalse(self.expediente.puede_avanzar())

    def test_08_rechaza_expediente_sin_actividades(self):
        with self.assertRaises(ValidationError):
            asignar_reglas_expediente(self.expediente)

    def test_09_permite_asignar_explicitamente_a_expediente_existente(self):
        self.expediente.crear_actividades_iniciales()
        self.configurar(self.catalogo1)
        self.configurar(self.catalogo2)
        self.assertEqual(asignar_reglas_expediente(self.expediente), 2)
        self.assertEqual(asignar_reglas_expediente(self.expediente), 0)

    def test_10_no_toca_otro_expediente(self):
        otro_alumno = get_user_model().objects.create_user(username="otro_alumno_13")
        otro = ExpedienteMovilidad.objects.create(alumno=otro_alumno, convocatoria=self.conv)
        otro.crear_actividades_iniciales()
        self.configurar(self.catalogo1)
        self.configurar(self.catalogo2)
        self.expediente.crear_actividades_iniciales(asignar_reglas=True)
        self.assertEqual(ReglaActividadExpediente.objects.filter(
            actividad_expediente__expediente=otro).count(), 0)
