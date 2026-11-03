"""Evaluación consultiva de reglas congeladas por expediente (actualización 14).

No cambia estados, fechas, permisos, historial ni archivos. Su resultado NO
concede autorización de avance: el mecanismo operativo sigue siendo el legado.
El estado documental se presenta como información, nunca como acreditación.
"""
from dataclasses import dataclass
from typing import Tuple

from .models import (
    ActividadExpediente,
    DocumentoExpediente,
    ExpedienteMovilidad,
    PoliticaRegla,
    ReglaActividadExpediente,
)


PERMITIDO = "PERMITIDO"
BLOQUEADO = "BLOQUEADO"
SIN_CONFIGURAR = "SIN_CONFIGURAR"


@dataclass(frozen=True)
class DetalleEvaluacion:
    actividad_id: int
    nombre: str
    politica: str
    estado_actividad: str
    diagnostico: str
    motivo: str
    documentos_cargados: int = 0
    documentos_aprobados: int = 0


@dataclass(frozen=True)
class ResultadoEvaluacion:
    expediente_id: int
    etapa: str
    resultado: str
    detalles: Tuple[DetalleEvaluacion, ...]
    advertencias: Tuple[str, ...]
    requiere_validacion_documental: bool = True

    @property
    def puede_autorizar(self):
        """Un diagnóstico informativo nunca autoriza una transición."""
        return False


def evaluar_etapa_expediente(expediente):
    """Lee todas las actividades de la etapa y sus reglas asignadas.

    PERMITIDO indica únicamente que las reglas *modeladas* se satisfacen.
    NO comprueba suficiencia documental, identidad/autorización de quien valida,
    ni requisitos institucionales externos todavía no parametrizados.
    Una falta de configuración predomina sobre un bloqueo conocido para impedir
    que se interprete como decisión completa; los bloqueos se listan en detalles.
    """
    if not isinstance(expediente, ExpedienteMovilidad) or not expediente.pk:
        raise ValueError("Se requiere un expediente guardado.")

    expediente = ExpedienteMovilidad.objects.get(pk=expediente.pk)
    if expediente.estado not in expediente.SIGUIENTE_ESTADO:
        return ResultadoEvaluacion(
            expediente.pk, expediente.estado, BLOQUEADO, (),
            ("La etapa es terminal o no permite transición.",),
        )

    actividades = list(
        ActividadExpediente.objects.filter(
            expediente=expediente,
            actividad_proceso__estado_expediente=expediente.estado,
        ).select_related("actividad_proceso")
        .order_by("actividad_proceso__orden", "pk")
    )
    if not actividades:
        return ResultadoEvaluacion(
            expediente.pk, expediente.estado, SIN_CONFIGURAR, (),
            ("No hay actividades registradas para la etapa actual.",),
        )

    copias = {
        r.actividad_expediente_id: r
        for r in ReglaActividadExpediente.objects.filter(
            actividad_expediente_id__in=[a.pk for a in actividades]
        )
    }
    conteos = {}
    for fila in (
        DocumentoExpediente.objects.filter(
            expediente=expediente,
            actividad_id__in=[a.pk for a in actividades],
        ).values_list("actividad_id", "estado")
    ):
        actividad_id, estado_documento = fila
        total, aprobados = conteos.get(actividad_id, (0, 0))
        conteos[actividad_id] = (
            total + 1,
            aprobados + (estado_documento == DocumentoExpediente.Estado.APROBADO),
        )

    detalles = []
    faltante = False
    bloqueado = False
    for a in actividades:
        regla = copias.get(a.pk)
        total, aprobados = conteos.get(a.pk, (0, 0))
        diagnostico = PERMITIDO
        motivo = ""
        politica = regla.politica if regla else "SIN_REGLA"

        if regla is None:
            diagnostico, motivo = SIN_CONFIGURAR, "Sin copia de regla asignada al expediente."
        elif regla.politica not in PoliticaRegla.values:
            diagnostico, motivo = SIN_CONFIGURAR, "Política de regla desconocida."
        elif regla.politica == PoliticaRegla.SEGUIMIENTO:
            motivo = "Actividad de seguimiento: no bloquea por esta política."
        else:
            # BLOQUEANTE aplica por defecto. CONDICIONAL requiere resolución.
            if regla.politica == PoliticaRegla.CONDICIONAL and regla.aplicabilidad == regla.Aplicabilidad.SIN_RESOLVER:
                diagnostico, motivo = SIN_CONFIGURAR, "La condición de aplicabilidad no está resuelta."
            elif regla.aplicabilidad == regla.Aplicabilidad.NO_APLICA:
                if not (regla.justificacion_no_aplica.strip() and regla.validado_por_id and regla.validado_en):
                    diagnostico, motivo = BLOQUEADO, "NO_APLICA sin justificación y validación completas."
                elif a.estado != a.Estado.NO_APLICA:
                    diagnostico, motivo = BLOQUEADO, "La regla indica NO_APLICA, pero el estado de actividad no coincide."
                else:
                    motivo = "No aplicabilidad justificada y registrada."
            elif a.estado == a.Estado.NO_APLICA:
                diagnostico, motivo = BLOQUEADO, "La actividad indica NO_APLICA sin regla validada."
            elif a.estado == a.Estado.COMPLETADA:
                motivo = "Actividad completada; evidencia documental aún no evaluada."
            else:
                diagnostico, motivo = BLOQUEADO, "Actividad aplicable sin completar."

        if diagnostico == SIN_CONFIGURAR:
            faltante = True
        elif diagnostico == BLOQUEADO:
            bloqueado = True
        detalles.append(DetalleEvaluacion(
            a.pk, a.actividad_proceso.nombre, politica, a.estado,
            diagnostico, motivo, total, aprobados,
        ))

    estado = SIN_CONFIGURAR if faltante else BLOQUEADO if bloqueado else PERMITIDO
    avisos = ["La evidencia documental no interviene aún en este diagnóstico; un archivo aprobado no acredita por sí solo la actividad."]
    if faltante:
        avisos.append("Configuración incompleta: el resultado no autoriza avance.")
    if estado == PERMITIDO:
        avisos.append("PERMITIDO es una evaluación consultiva, no una autorización para avanzar.")
    return ResultadoEvaluacion(expediente.pk, expediente.estado, estado, tuple(detalles), tuple(avisos))
