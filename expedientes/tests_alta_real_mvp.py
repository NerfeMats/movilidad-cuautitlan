from datetime import date

from django.contrib import admin
from django.test import SimpleTestCase
from django.core.exceptions import ValidationError

from .admin import ExpedienteAltaAdminForm, ExpedienteMovilidadAdmin
from .models import ExpedienteMovilidad, ActividadExpediente


class AltaRealMVPTests(SimpleTestCase):
    def test_avance_masivo_desactivado(self):
        panel = ExpedienteMovilidadAdmin(ExpedienteMovilidad, admin.site)
        self.assertEqual(panel.actions, [])
        self.assertNotIn("avanzar_estado_seleccionados", dir(panel))

    def test_fecha_inicio_digital_se_conserva(self):
        campo = ExpedienteMovilidad._meta.get_field("fecha_inicio")
        self.assertTrue(campo.auto_now_add)

    def test_fecha_real_es_opcional(self):
        campo = ExpedienteMovilidad._meta.get_field("fecha_inicio_real_movilidad")
        self.assertTrue(campo.null)
        self.assertTrue(campo.blank)

    def test_fecha_cumplimiento_historico_es_opcional(self):
        campo = ActividadExpediente._meta.get_field("fecha_cumplimiento_real")
        self.assertTrue(campo.null)
        self.assertTrue(campo.blank)

    def test_formulario_excepcional_rechaza_estado_inconsistente(self):
        from django.forms.utils import ErrorDict
        formulario = ExpedienteAltaAdminForm()
        formulario._errors = ErrorDict()
        formulario.cleaned_data = {
            "tipo_alta": ExpedienteMovilidad.TipoAlta.EXCEPCIONAL,
            "estado_inicial": ExpedienteMovilidad.Estado.EN_REVISION,
            "estado": ExpedienteMovilidad.Estado.INICIADO,
        }
        formulario.clean()
        self.assertIn("estado", formulario._errors)

    def test_formulario_normal_rechaza_estado_avanzado(self):
        from django.forms.utils import ErrorDict
        formulario = ExpedienteAltaAdminForm()
        formulario._errors = ErrorDict()
        formulario.cleaned_data = {
            "tipo_alta": ExpedienteMovilidad.TipoAlta.NORMAL,
            "estado_inicial": ExpedienteMovilidad.Estado.INICIADO,
            "estado": ExpedienteMovilidad.Estado.EN_REVISION,
        }
        formulario.clean()
        self.assertIn("estado", formulario._errors)

    def test_alta_excepcional_requiere_motivo_y_recepcion(self):
        expediente = ExpedienteMovilidad(
            tipo_alta=ExpedienteMovilidad.TipoAlta.EXCEPCIONAL,
            estado_inicial=ExpedienteMovilidad.Estado.EN_REVISION,
            estado=ExpedienteMovilidad.Estado.EN_REVISION,
        )
        with self.assertRaises(ValidationError) as resultado:
            expediente.clean()
        self.assertIn("motivo_alta_excepcional", resultado.exception.message_dict)
        self.assertIn("fecha_recepcion_area", resultado.exception.message_dict)

    def test_alta_excepcional_con_datos_acreditados(self):
        expediente = ExpedienteMovilidad(
            tipo_alta=ExpedienteMovilidad.TipoAlta.EXCEPCIONAL,
            estado_inicial=ExpedienteMovilidad.Estado.EN_REVISION,
            estado=ExpedienteMovilidad.Estado.EN_REVISION,
            fecha_recepcion_area=date(2026, 10, 1),
            fecha_inicio_real_movilidad=date(2026, 8, 15),
            motivo_alta_excepcional="Recibido en etapa de revision",
        )
        self.assertIsNone(expediente.clean())

