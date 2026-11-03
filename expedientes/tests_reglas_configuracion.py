"""Fase 2: integridad y aislamiento, sin activar nuevas reglas de avance."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from convocatorias.models import Convocatoria, TipoMovilidad
from expedientes.models import (
    ActividadExpediente, ActividadProceso, ExpedienteMovilidad,
    ReglaActividadConvocatoria, ReglaActividadExpediente,
    EstadoConfiguracion, PoliticaRegla,
)


class ConfiguracionReglasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tipo = TipoMovilidad.objects.create(nombre="Tipo modelo reglas")
        cls.otro_tipo = TipoMovilidad.objects.create(nombre="Tipo diferente reglas")
        cls.conv = Convocatoria.objects.create(tipo_movilidad=cls.tipo, titulo="Conv fase2", ciclo="PRIMAVERA", anio=2027)
        cls.otra_conv = Convocatoria.objects.create(tipo_movilidad=cls.tipo, titulo="Conv fase2 otra", ciclo="OTONO", anio=2027)
        cls.alumno = get_user_model().objects.create_user(username="fase2_alumno")
        cls.responsable = get_user_model().objects.create_user(username="fase2_responsable", is_staff=True)
        cls.expediente = ExpedienteMovilidad.objects.create(alumno=cls.alumno, convocatoria=cls.conv, estado=ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE)
        cls.catalogo = ActividadProceso.objects.create(
            tipo_movilidad=cls.tipo, nombre="Actividad fase2", etapa="ANTES",
            responsable="ALUMNO", orden=1, obligatorio=True,
            estado_expediente=ExpedienteMovilidad.Estado.INTEGRANDO_EXPEDIENTE,
        )
        cls.actividad = ActividadExpediente.objects.create(expediente=cls.expediente, actividad_proceso=cls.catalogo)

    def regla(self, **campos):
        valores = dict(
            convocatoria=self.conv, actividad_proceso=self.catalogo,
            estado_configuracion=EstadoConfiguracion.DEFINIDA,
            politica=PoliticaRegla.BLOQUEANTE,
            fundamento="Criterio de prueba, no validado institucionalmente",
        )
        valores.update(campos)
        return ReglaActividadConvocatoria.objects.create(**valores)

    def test_01_regla_sin_definir_no_es_automaticamente_seguimiento(self):
        regla = ReglaActividadConvocatoria.objects.create(convocatoria=self.conv, actividad_proceso=self.catalogo)
        self.assertEqual(regla.estado_configuracion, EstadoConfiguracion.SIN_DEFINIR)
        with self.assertRaises(ValidationError):
            ReglaActividadExpediente.crear_copia(self.actividad, regla)

    def test_02_regla_definida_necesita_fundamento(self):
        regla = ReglaActividadConvocatoria(convocatoria=self.conv, actividad_proceso=self.catalogo,
                                         estado_configuracion=EstadoConfiguracion.DEFINIDA)
        with self.assertRaises(ValidationError):
            regla.full_clean()

    def test_03_condicional_necesita_condicion_explicita(self):
        regla = ReglaActividadConvocatoria(convocatoria=self.conv, actividad_proceso=self.catalogo,
            estado_configuracion=EstadoConfiguracion.DEFINIDA, politica=PoliticaRegla.CONDICIONAL, fundamento="Prueba")
        with self.assertRaises(ValidationError):
            regla.full_clean()
        regla.condicion_aplicabilidad = "Solo cuando el destino requiera visa"
        regla.full_clean()

    def test_04_regla_no_acepta_actividad_de_otro_tipo(self):
        otra_actividad = ActividadProceso.objects.create(tipo_movilidad=self.otro_tipo, nombre="Incompatible",
            etapa="ANTES", responsable="ALUMNO", estado_expediente="INICIADO")
        regla = ReglaActividadConvocatoria(convocatoria=self.conv, actividad_proceso=otra_actividad)
        with self.assertRaises(ValidationError):
            regla.full_clean()

    def test_05_no_duplicar_regla_convocatoria_actividad(self):
        self.regla()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.regla()

    def test_06_copia_no_se_modifica_cuando_cambia_convocatoria(self):
        regla = self.regla()
        copia = ReglaActividadExpediente.crear_copia(self.actividad, regla)
        self.assertEqual(copia.politica, PoliticaRegla.BLOQUEANTE)
        regla.politica = PoliticaRegla.SEGUIMIENTO
        regla.save(update_fields=["politica"])
        copia.refresh_from_db()
        self.assertEqual(copia.politica, PoliticaRegla.BLOQUEANTE)

    def test_07_rechaza_regla_de_otra_convocatoria(self):
        regla = self.regla(convocatoria=self.otra_conv)
        with self.assertRaises(ValidationError):
            ReglaActividadExpediente.crear_copia(self.actividad, regla)

    def test_08_no_aplica_requiere_justificacion_y_validacion(self):
        regla = self.regla()
        copia = ReglaActividadExpediente.crear_copia(self.actividad, regla)
        copia.aplicabilidad = ReglaActividadExpediente.Aplicabilidad.NO_APLICA
        with self.assertRaises(ValidationError):
            copia.full_clean()
        copia.justificacion_no_aplica = "El destino no requiere este trámite"
        copia.validado_por = self.responsable
        copia.validado_en = timezone.now()
        copia.full_clean()

    def test_09_migracion_no_inserta_reglas_ni_cambia_avance(self):
        self.assertFalse(ReglaActividadConvocatoria.objects.exists())
        self.assertFalse(ReglaActividadExpediente.objects.exists())
        self.assertFalse(self.expediente.puede_avanzar())
        self.actividad.estado = ActividadExpediente.Estado.COMPLETADA
        self.actividad.save()
        self.assertTrue(self.expediente.puede_avanzar())

    def test_10_actividad_solo_puede_tener_una_copia(self):
        regla = self.regla()
        ReglaActividadExpediente.crear_copia(self.actividad, regla)
        with self.assertRaises(ValidationError):
            ReglaActividadExpediente.crear_copia(self.actividad, regla)
