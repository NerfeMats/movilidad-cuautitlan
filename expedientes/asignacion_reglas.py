"""Asignacion explicita de reglas versionadas por expediente.

No cambia las decisiones de avance ni rellena reglas ausentes. Una convocatoria
incompleta genera un error, sin asignaciones parciales. Compatible con Django 6.
"""
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    ActividadExpediente,
    EstadoConfiguracion,
    ExpedienteMovilidad,
    ReglaActividadConvocatoria,
    ReglaActividadExpediente,
)


@transaction.atomic
def asignar_reglas_expediente(expediente):
    """Crea copias solo para actividades existentes y reglas DEFINIDAS.

    Devuelve el numero de copias creadas. Es idempotente: una copia existente
    se respeta, incluso si el catalogo cambia. No usa reglas del catalogo
    como reemplazo silencioso de reglas de convocatoria.
    """
    if not isinstance(expediente, ExpedienteMovilidad) or not expediente.pk:
        raise ValidationError("Se necesita un expediente guardado.")

    expediente = ExpedienteMovilidad.objects.select_for_update().get(pk=expediente.pk)
    actividades = list(
        ActividadExpediente.objects.filter(expediente=expediente)
        .select_related("actividad_proceso")
        .order_by("pk")
    )
    if not actividades:
        raise ValidationError("El expediente no tiene actividades; no se pueden asignar reglas.")

    reglas = {
        regla.actividad_proceso_id: regla
        for regla in ReglaActividadConvocatoria.objects.filter(
            convocatoria_id=expediente.convocatoria_id,
            actividad_proceso_id__in=[a.actividad_proceso_id for a in actividades],
        ).select_related("convocatoria", "actividad_proceso")
    }
    sin_regla = [
        a.actividad_proceso.nombre
        for a in actividades
        if a.actividad_proceso_id not in reglas
        or reglas[a.actividad_proceso_id].estado_configuracion != EstadoConfiguracion.DEFINIDA
    ]
    if sin_regla:
        raise ValidationError(
            "No se pueden asignar reglas: hay actividades sin una regla DEFINIDA: "
            + ", ".join(sin_regla)
        )

    existentes = {
        copia.actividad_expediente_id: copia
        for copia in ReglaActividadExpediente.objects.filter(
            actividad_expediente__expediente=expediente
        )
    }
    # Validar incluso en reintentos: no alterar ni reemplazar copias anteriores.
    for actividad in actividades:
        regla = reglas[actividad.actividad_proceso_id]
        regla.full_clean()
        copia = existentes.get(actividad.pk)
        if copia is not None:
            if copia.regla_origen_id != regla.pk:
                raise ValidationError(
                    "La actividad ya tiene una copia de otra regla; requiere revision expresa."
                )
            copia.full_clean()

    creadas = 0
    for actividad in actividades:
        if actividad.pk not in existentes:
            ReglaActividadExpediente.crear_copia(
                actividad, reglas[actividad.actividad_proceso_id]
            )
            creadas += 1
    return creadas
