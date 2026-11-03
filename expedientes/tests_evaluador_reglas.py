"""Pruebas de la actualización 14. Base aislada de Django TestCase."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from convocatorias.models import Convocatoria, TipoMovilidad
from expedientes.evaluador_reglas import (
    PERMITIDO, BLOQUEADO, SIN_CONFIGURAR, evaluar_etapa_expediente,
)
from expedientes.models import (
    ActividadProceso, ActividadExpediente, DocumentoExpediente,
    ExpedienteMovilidad, PoliticaRegla, EstadoConfiguracion,
    ReglaActividadConvocatoria, ReglaActividadExpediente,
)


class EvaluadorReglasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tipo = TipoMovilidad.objects.create(nombre="Evaluador 14")
        cls.conv = Convocatoria.objects.create(
            tipo_movilidad=cls.tipo, titulo="Evaluador 14 convocatoria",
            ciclo=Convocatoria.Ciclo.PRIMAVERA, anio=2027,
        )
        cls.alumno = get_user_model().objects.create_user(username="eval14_alumno")
        cls.validador = get_user_model().objects.create_user(username="eval14_validador", is_staff=True)
        cls.e = ExpedienteMovilidad.objects.create(
            alumno=cls.alumno, convocatoria=cls.conv, estado=ExpedienteMovilidad.Estado.EN_REVISION,
        )
        cls.proceso = ActividadProceso.objects.create(
            tipo_movilidad=cls.tipo, nombre="Validación 14", etapa="ANTES",
            responsable="ALUMNO", obligatorio=False,
            estado_expediente=ExpedienteMovilidad.Estado.EN_REVISION,
            activo=True, orden=1,
        )

    def crear_actividad(self):
        return ActividadExpediente.objects.create(
            expediente=self.e, actividad_proceso=self.proceso,
            estado=ActividadExpediente.Estado.PENDIENTE,
        )

    def regla(self, actividad, politica=PoliticaRegla.BLOQUEANTE):
        origen = ReglaActividadConvocatoria.objects.create(
            convocatoria=self.conv, actividad_proceso=self.proceso,
            politica=politica, estado_configuracion=EstadoConfiguracion.DEFINIDA,
            fundamento="Solo para prueba automatizada",
            condicion_aplicabilidad="Si requiere trámite" if politica == PoliticaRegla.CONDICIONAL else "",
        )
        return ReglaActividadExpediente.crear_copia(actividad, origen)

    def test_01_sin_actividades_es_sin_configurar(self):
        r = evaluar_etapa_expediente(self.e)
        self.assertEqual(r.resultado, SIN_CONFIGURAR)
        self.assertFalse(r.puede_autorizar)

    def test_02_sin_copia_es_sin_configurar(self):
        self.crear_actividad()
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, SIN_CONFIGURAR)

    def test_03_bloqueante_pendiente_bloquea(self):
        a = self.crear_actividad()
        self.regla(a)
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, BLOQUEADO)

    def test_04_bloqueante_completada_diagnostico_permitido(self):
        a = self.crear_actividad()
        self.regla(a)
        a.estado = a.Estado.COMPLETADA
        a.save()
        r = evaluar_etapa_expediente(self.e)
        self.assertEqual(r.resultado, PERMITIDO)
        self.assertFalse(r.puede_autorizar)

    def test_05_seguimiento_pendiente_no_bloquea(self):
        a = self.crear_actividad()
        self.regla(a, PoliticaRegla.SEGUIMIENTO)
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, PERMITIDO)

    def test_06_condicional_sin_resolver_no_se_autoriza(self):
        a = self.crear_actividad()
        self.regla(a, PoliticaRegla.CONDICIONAL)
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, SIN_CONFIGURAR)

    def test_07_condicional_aplica_pendiente_bloquea(self):
        a = self.crear_actividad()
        r = self.regla(a, PoliticaRegla.CONDICIONAL)
        r.aplicabilidad = r.Aplicabilidad.APLICA
        r.save()
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, BLOQUEADO)

    def test_08_no_aplica_sin_justificacion_es_bloqueado(self):
        a = self.crear_actividad()
        r = self.regla(a, PoliticaRegla.CONDICIONAL)
        r.aplicabilidad = r.Aplicabilidad.NO_APLICA
        r.save()
        a.estado = a.Estado.NO_APLICA
        a.save()
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, BLOQUEADO)

    def test_09_no_aplica_justificado_y_validado(self):
        a = self.crear_actividad()
        r = self.regla(a, PoliticaRegla.CONDICIONAL)
        r.aplicabilidad = r.Aplicabilidad.NO_APLICA
        r.justificacion_no_aplica = "No requiere visa por destino documentado"
        r.validado_por = self.validador
        r.validado_en = timezone.now()
        r.full_clean()
        r.save()
        a.estado = a.Estado.NO_APLICA
        a.save()
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, PERMITIDO)

    def test_10_no_aplica_estado_desincronizado_bloquea(self):
        a = self.crear_actividad()
        r = self.regla(a, PoliticaRegla.CONDICIONAL)
        r.aplicabilidad = r.Aplicabilidad.NO_APLICA
        r.justificacion_no_aplica = "No aplica por criterio"
        r.validado_por = self.validador
        r.validado_en = timezone.now()
        r.save()
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, BLOQUEADO)

    def test_11_terminal_cerrado_bloquea(self):
        self.e.estado = self.e.Estado.CERRADO
        self.e.save()
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, BLOQUEADO)

    def test_12_no_modifica_estado_ni_historial(self):
        a = self.crear_actividad()
        self.regla(a)
        estado_antes = self.e.estado
        evaluar_etapa_expediente(self.e)
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, estado_antes)
        self.assertEqual(self.e.historial.count(), 0)

    def test_13_documentos_solo_informativos(self):
        a = self.crear_actividad()
        self.regla(a)
        DocumentoExpediente.objects.create(
            expediente=self.e, actividad=a, nombre="Evidencia evaluador",
            estado=DocumentoExpediente.Estado.APROBADO,
            archivo="archivo-de-prueba-sin-escritura.pdf",
        )
        r = evaluar_etapa_expediente(self.e)
        self.assertEqual(r.resultado, BLOQUEADO)
        self.assertEqual(r.detalles[0].documentos_aprobados, 1)
        self.assertTrue(r.requiere_validacion_documental)

    def test_14_no_cambia_puede_avanzar_legacy(self):
        a = self.crear_actividad()
        self.regla(a, PoliticaRegla.BLOQUEANTE)
        self.assertEqual(evaluar_etapa_expediente(self.e).resultado, BLOQUEADO)
        self.assertTrue(self.e.puede_avanzar())  # catálogo obligatorio=False
