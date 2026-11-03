"""Regresion visual y de aislamiento del centro por expediente (19.1)."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, RequestFactory
from django.urls import reverse
from django.template.loader import get_template
from django.http import HttpResponseRedirect

from . import panel_responsable
from .seguimiento_agrupacion import agrupar_pendientes


class AgrupacionSeguimiento191Tests(SimpleTestCase):
    def expediente(self, pk, usuario):
        return SimpleNamespace(pk=pk, alumno=SimpleNamespace(username=usuario))

    def actividad(self, exp, responsable):
        proceso = SimpleNamespace(get_responsable_display=lambda: responsable)
        return SimpleNamespace(expediente=exp, actividad_proceso=proceso)

    def accion(self, exp, responsable):
        return SimpleNamespace(expediente=exp, get_responsable_display=lambda: responsable)

    def test_un_grupo_por_expediente_con_varias_actividades(self):
        exp = self.expediente(5, "alumno_demo")
        grupos = agrupar_pendientes([
            self.actividad(exp, "Alumno"),
            self.actividad(exp, "Alumno"),
            self.actividad(exp, "DAAE"),
        ], [])
        self.assertEqual(len(grupos), 1)
        self.assertEqual(grupos[0]["total"], 3)
        self.assertEqual(grupos[0]["responsables"], [
            {"nombre": "Alumno", "total": 2},
            {"nombre": "DAAE", "total": 1},
        ])

    def test_mismo_alumno_con_expedientes_distintos_no_se_fusiona(self):
        exp1 = self.expediente(5, "mismo_alumno")
        exp2 = self.expediente(9, "mismo_alumno")
        grupos = agrupar_pendientes([self.actividad(exp1, "Alumno"), self.actividad(exp2, "DAAE")], [])
        self.assertEqual([g["expediente"].pk for g in grupos], [5, 9])

    def test_acciones_y_actividades_se_agrupan_sin_duplicar(self):
        exp1 = self.expediente(7, "prueba")
        exp2 = self.expediente(8, "otra")
        grupos = agrupar_pendientes([self.actividad(exp1, "Titular")], [self.accion(exp1, "DAAE"), self.accion(exp2, "Alumno")])
        self.assertEqual([g["total"] for g in grupos], [2, 1])
        self.assertEqual(len(grupos[0]["actividades"]), 1)
        self.assertEqual(len(grupos[0]["acciones"]), 1)

    def test_titular_en_mis_pendientes_es_redirigido_al_centro(self):
        solicitud = RequestFactory().get(reverse("expedientes:mis_pendientes"))
        solicitud.user = SimpleNamespace(is_authenticated=True, is_active=True, is_staff=True,
                                         has_perm=lambda permiso: permiso == "expedientes.view_expedientemovilidad")
        respuesta = panel_responsable.mis_pendientes(solicitud)
        self.assertIsInstance(respuesta, HttpResponseRedirect)
        self.assertEqual(respuesta["Location"], reverse("expedientes:centro_seguimiento"))

    def test_plantilla_usa_desplegables_y_compila(self):
        plantilla = get_template("expedientes/centro_seguimiento.html")
        self.assertIsNotNone(plantilla)
        from pathlib import Path
        from django.conf import settings
        fuente = (Path(settings.BASE_DIR) / "expedientes" / "templates" / "expedientes" / "centro_seguimiento.html").read_text(encoding="utf-8")
        self.assertIn("<details", fuente)
        self.assertIn("{% for grupo in grupos %}", fuente)
        self.assertIn("{% for a in grupo.actividades %}", fuente)
        self.assertIn("{% for a in grupo.acciones %}", fuente)
