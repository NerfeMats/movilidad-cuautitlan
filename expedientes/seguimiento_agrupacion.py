"""Presentacion consolidada por expediente, sin persistencia adicional."""
from collections import Counter


def agrupar_pendientes(actividades, acciones):
    """Agrupa por PK de expediente, no por alumno; conserva tareas y gestiones."""
    grupos = {}

    def obtener(expediente):
        grupo = grupos.get(expediente.pk)
        if grupo is None:
            grupo = {
                "expediente": expediente,
                "actividades": [],
                "acciones": [],
                "responsables": [],
                "total": 0,
            }
            grupos[expediente.pk] = grupo
        return grupo

    for actividad in actividades:
        grupo = obtener(actividad.expediente)
        grupo["actividades"].append(actividad)
    for accion in acciones:
        grupo = obtener(accion.expediente)
        grupo["acciones"].append(accion)

    for grupo in grupos.values():
        grupo["total"] = len(grupo["actividades"]) + len(grupo["acciones"])
        cuentas = Counter(
            [a.actividad_proceso.get_responsable_display() for a in grupo["actividades"]]
            + [a.get_responsable_display() for a in grupo["acciones"]]
        )
        grupo["responsables"] = [
            {"nombre": nombre, "total": total}
            for nombre, total in sorted(cuentas.items())
        ]

    return sorted(grupos.values(), key=lambda g: g["expediente"].pk)
