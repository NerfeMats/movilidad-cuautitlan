"""Regresiones del alta administrativa 16.1, sin datos reales."""
from unittest.mock import patch

from django.contrib import admin
from django.test import SimpleTestCase

from .admin import ExpedienteAltaAdminForm, ExpedienteMovilidadAdmin
from .models import ExpedienteMovilidad


class AltaAdmin161Tests(SimpleTestCase):
    def setUp(self):
        self.panel = ExpedienteMovilidadAdmin(ExpedienteMovilidad, admin.site)

    def test_estado_no_aparece_durante_alta(self):
        campos = [
            campo for _, opciones in self.panel.get_fieldsets(None, None)
            for campo in opciones["fields"]
        ]
        self.assertIn("estado_inicial", campos)
        self.assertNotIn("estado", campos)
        self.assertIn("estado", self.panel.get_exclude(None, None))

    def test_estado_se_conserva_como_dato_de_lectura_en_edicion(self):
        obj = ExpedienteMovilidad(pk=999)
        campos = [
            campo for _, opciones in self.panel.get_fieldsets(None, obj)
            for campo in opciones["fields"]
        ]
        self.assertIn("estado", campos)
        self.assertIn("estado", self.panel.get_readonly_fields(None, obj))
        self.assertNotIn("estado", self.panel.get_exclude(None, obj) or ())

    def test_alta_excepcional_asigna_estado_inicial_en_servidor(self):
        form = ExpedienteAltaAdminForm()
        form.cleaned_data = {"estado_inicial": ExpedienteMovilidad.Estado.EN_REVISION}
        with patch("django.forms.ModelForm.save", return_value=form.instance) as base_save:
            expediente = form.save(commit=False)
        self.assertEqual(expediente.estado, ExpedienteMovilidad.Estado.EN_REVISION)
        base_save.assert_called_once_with(commit=False)

    def test_alta_normal_asigna_iniciado(self):
        form = ExpedienteAltaAdminForm()
        form.cleaned_data = {"estado_inicial": ExpedienteMovilidad.Estado.INICIADO}
        with patch("django.forms.ModelForm.save", return_value=form.instance):
            form.save(commit=False)
        self.assertEqual(form.instance.estado, ExpedienteMovilidad.Estado.INICIADO)

    def test_edicion_no_sobrescribe_estado_actual(self):
        form = ExpedienteAltaAdminForm(instance=ExpedienteMovilidad(
            pk=999,
            estado=ExpedienteMovilidad.Estado.EN_MOVILIDAD,
            estado_inicial=ExpedienteMovilidad.Estado.EN_REVISION,
        ))
        form.cleaned_data = {"estado_inicial": ExpedienteMovilidad.Estado.INICIADO}
        with patch("django.forms.ModelForm.save", return_value=form.instance):
            form.save(commit=False)
        self.assertEqual(form.instance.estado, ExpedienteMovilidad.Estado.EN_MOVILIDAD)
