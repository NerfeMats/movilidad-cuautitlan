from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Q
from django.utils import timezone

from .models import ExpedienteMovilidad, DocumentoExpediente, ActividadExpediente, AccionSeguimiento, RecordatorioSeguimiento
from .seguimiento_agrupacion import agrupar_pendientes


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
        "resumen_seguimiento": resumen_seguimiento(),
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
        "actividades_vinculables": actividades,
        "documentos_vinculados": (expediente.documentos.filter(actividad__isnull=False).select_related("actividad__actividad_proceso") if puede_ver_documentos and hasattr(expediente, "documentos") else []),
    })


def actividades_exigibles():
    """Actuales no cerradas, excluye las heredadas sin registro y las futuras."""
    return (ActividadExpediente.objects
        .filter(expediente__activo=True,
                actividad_proceso__estado_expediente=models_F("expediente__estado"))
        .exclude(expediente__estado__in=["CERRADO", "CANCELADO"])
        .exclude(estado__in=["COMPLETADA", "NO_APLICA", "NO_REGISTRADA"])
        .select_related("expediente__alumno", "actividad_proceso", "expediente__convocatoria"))


# Alias explícito para comparar columnas, sin consultas individuales por expediente.
from django.db.models import F as models_F


def resumen_seguimiento():
    actividades = actividades_exigibles()
    acciones = (AccionSeguimiento.objects
               .filter(expediente__activo=True)
               .exclude(expediente__estado__in=["CERRADO", "CANCELADO"])
               .exclude(estado__in=["COMPLETADA", "CANCELADA"])
               .select_related("expediente__alumno", "encargado_seguimiento"))
    return {"actividades": actividades, "acciones": acciones,
            "hoy": timezone.localdate(),
            "borradores": RecordatorioSeguimiento.objects.filter(estado="BORRADOR").count()}


@login_required
def centro_seguimiento(request):
    if not es_responsable_autorizado(request.user):
        raise PermissionDenied("Sin permiso de seguimiento global")
    datos = resumen_seguimiento()
    # Las consultas se materializan una vez; cada expediente se muestra una sola vez.
    actividades = list(datos["actividades"])
    acciones = list(datos["acciones"])
    datos["grupos"] = agrupar_pendientes(actividades, acciones)
    datos["total_actividades"] = len(actividades)
    datos["total_acciones"] = len(acciones)
    # La vista no ejecuta envío ni altera estados.
    return render(request, "expedientes/centro_seguimiento.html", datos)


@login_required
def mis_pendientes(request):
    if not request.user.is_active:
        raise PermissionDenied("Cuenta inactiva")
    # Esta ruta es para alumnos; evitar bandejas vacias y ambiguas al titular.
    if request.user.is_staff:
        if es_responsable_autorizado(request.user):
            return redirect("expedientes:centro_seguimiento")
        raise PermissionDenied("La bandeja de alumnos no corresponde a personal administrativo")
    actividades = (actividades_exigibles()
        .filter(expediente__alumno=request.user, actividad_proceso__responsable="ALUMNO"))
    acciones = (AccionSeguimiento.objects
        .filter(expediente__alumno=request.user, responsable="ALUMNO", visible_alumno=True)
        .exclude(estado__in=["COMPLETADA", "CANCELADA"])
        .select_related("expediente"))
    return render(request, "expedientes/mis_pendientes.html", {
        "actividades": actividades, "acciones": acciones, "hoy": timezone.localdate(),
    })
