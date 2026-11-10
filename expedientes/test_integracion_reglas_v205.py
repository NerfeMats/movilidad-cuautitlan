from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from convocatorias.models import Convocatoria, TipoMovilidad
from expedientes.models import ExpedienteMovilidad
from expedientes.evaluador_reglas import ResultadoEvaluacion


class DiagnosticoReglasIntegracionTests(TestCase):

    @patch("expedientes.panel_responsable.es_responsable_autorizado",
           return_value=True)
    @patch("expedientes.evaluador_reglas.evaluar_etapa_expediente")
    def test_expediente_real_muestra_diagnostico(
        self, evaluar, autorizado
    ):
        User = get_user_model()

        usuario = User.objects.create_user(
            username="responsable_prueba_v205",
            password="clave_temporal",
            is_staff=True,
        )

        self.client.force_login(usuario)

        tipo = TipoMovilidad.objects.create(
            nombre="Internacional prueba v205"
        )

        convocatoria = Convocatoria.objects.create(
            tipo_movilidad=tipo,
            titulo="Convocatoria prueba v205",
            ciclo="PRIMAVERA",
            anio=2027,
        )

        alumno = User.objects.create_user(
            username="alumno_prueba_v205",
            password="clave_temporal",
        )

        expediente = ExpedienteMovilidad.objects.create(
            alumno=alumno,
            convocatoria=convocatoria,
        )

        evaluar.return_value = ResultadoEvaluacion(
            expediente_id=expediente.pk,
            etapa=expediente.estado,
            resultado="SIN_CONFIGURAR",
            detalles=(),
            advertencias=("Sin reglas asignadas.",),
        )

        respuesta = self.client.get(
            reverse("expedientes:centro_seguimiento"),
            {"vista": "reglas", "expediente": str(expediente.pk)},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.context["resultado_reglas_estado"],
            "SIN_CONFIGURAR",
        )
        self.assertContains(respuesta, "Configuraci\u00f3n pendiente")
        self.assertContains(respuesta, "Sin reglas asignadas.")
        evaluar.assert_called_once()
