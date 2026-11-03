from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from .models import ExpedienteMovilidad, DocumentoExpediente


def es_responsable_autorizado(user):
    return (
        user.is_authenticated
        and user.is_staff
        and user.has_perm("expedientes.view_expedientemovilidad")
    )


@login_required
def panel_responsable(request):
    if not es_responsable_autorizado(request.user):
        raise PermissionDenied("No tiene permiso para consultar todos los expedientes.")
    expedientes = (
        ExpedienteMovilidad.objects
        .select_related("alumno", "convocatoria", "convocatoria__tipo_movilidad")
        .order_by("-fecha_inicio")
    )
    return render(request, "expedientes/panel_responsable.html", {
        "expedientes": expedientes,
    })


@login_required
def ruta_responsable(request, pk):
    if not es_responsable_autorizado(request.user):
        raise PermissionDenied("No tiene permiso para consultar todos los expedientes.")
    expediente = get_object_or_404(
        ExpedienteMovilidad.objects
        .select_related("alumno", "convocatoria", "convocatoria__tipo_movilidad", "ies_destino")
        .prefetch_related("actividades__actividad_proceso"),
        pk=pk,
    )
    actividades = list(expediente.actividades.all())
    estaciones = []
    orden_actual = ExpedienteMovilidad.ORDEN_ESTADOS.get(expediente.estado)
    for codigo, nombre in ExpedienteMovilidad.Estado.choices:
        if codigo == ExpedienteMovilidad.Estado.CANCELADO:
            continue
        orden = ExpedienteMovilidad.ORDEN_ESTADOS[codigo]
        situacion = ("cancelada" if orden_actual is None else
                     "actual" if expediente.estado == codigo else
                     "recorrida" if orden < orden_actual else "futura")
        estaciones.append({
            "codigo": codigo,
            "nombre": nombre,
            "situacion": situacion,
            "actividades": [
                a for a in actividades
                if a.actividad_proceso.estado_expediente == codigo
            ],
        })

    # Los documentos historicos no tienen actividad asociada. La vista se limita
    # a consulta y no concede acceso por si misma al archivo: descargar_documento_web
    # conserva la comprobacion individual de permisos en abrir_documento().
    puede_ver_documentos = request.user.has_perm("expedientes.view_documentoexpediente")
    documentos_historicos = (
        DocumentoExpediente.objects
        .filter(expediente=expediente, actividad__isnull=True)
        .order_by("pk")
        if puede_ver_documentos else DocumentoExpediente.objects.none()
    )

    return render(request, "expedientes/ruta_responsable.html", {
        "expediente": expediente,
        "estaciones": estaciones,
        "puede_avanzar": expediente.puede_avanzar(),
        "documentos_historicos": documentos_historicos,
        "puede_ver_documentos": puede_ver_documentos,
    })
