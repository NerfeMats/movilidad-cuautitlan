"""Proyecciones de solo lectura para el inicio del responsable (v21.1).
No cambian estados, no envian notificaciones y no acreditan cumplimiento.
"""
from .models import AccionSeguimiento, ActividadProceso


def construir_jornada(actividades, acciones, usuario):
    actividades = list(actividades)
    acciones = list(acciones)
    return {
        "gestiones": [a for a in acciones if a.encargado_seguimiento_id == usuario.pk],
        "recordar": [a for a in actividades if a.actividad_proceso.responsable == ActividadProceso.Responsable.ALUMNO],
        "esperando": [a for a in acciones if a.estado == AccionSeguimiento.Estado.ESPERANDO_RESPUESTA],
        "revision": [a for a in acciones if a.estado == AccionSeguimiento.Estado.REQUIERE_CORRECCION],
    }
