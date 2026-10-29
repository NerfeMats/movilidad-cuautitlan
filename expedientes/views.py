from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import ExpedienteMovilidad


@login_required
def lista_expedientes(request):
    expedientes = (
        ExpedienteMovilidad.objects
        .filter(alumno=request.user)
        .select_related(
            "convocatoria",
            "convocatoria__tipo_movilidad",
            "ies_destino",
        )
        .order_by("-fecha_inicio")
    )
    return render(request, "expedientes/lista_expedientes.html", {"expedientes": expedientes})


@login_required
def detalle_expediente(request, pk):
    # Se conserva la comprobación de propiedad: un alumno no puede consultar
    # el expediente de otro usuario alterando el identificador de la URL.
    expediente = get_object_or_404(
        ExpedienteMovilidad.objects
        .select_related(
            "convocatoria",
            "convocatoria__tipo_movilidad",
            "ies_destino",
        )
        .prefetch_related("actividades__actividad_proceso"),
        pk=pk,
        alumno=request.user,
    )

    actividades = list(expediente.actividades.all())
    orden_actual = ExpedienteMovilidad.ORDEN_ESTADOS.get(expediente.estado)
    cancelado = expediente.estado == ExpedienteMovilidad.Estado.CANCELADO
    estaciones = []
    for numero, (codigo, nombre) in enumerate(ExpedienteMovilidad.Estado.choices, start=1):
        if codigo == ExpedienteMovilidad.Estado.CANCELADO:
            continue
        orden = ExpedienteMovilidad.ORDEN_ESTADOS[codigo]
        if cancelado:
            situacion = "cancelada"
        elif codigo == expediente.estado:
            situacion = "actual"
        elif orden_actual is not None and orden < orden_actual:
            situacion = "recorrida"
        else:
            situacion = "futura"
        actividades_estacion = [
            a for a in actividades if a.actividad_proceso.estado_expediente == codigo
        ]
        estaciones.append({
            "numero": orden,
            "codigo": codigo,
            "nombre": nombre,
            "situacion": situacion,
            "actividades": actividades_estacion,
            "total": len(actividades_estacion),
        })

    contexto = {
        "expediente": expediente,
        "actividades": actividades,
        "estaciones": estaciones,
        "puede_avanzar": expediente.puede_avanzar(),
        "cancelado": cancelado,
    }
    return render(request, "expedientes/detalle_expediente.html", contexto)
