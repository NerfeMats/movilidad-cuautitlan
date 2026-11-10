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
    # V20.4: inventario de solo lectura. No altera la bandeja de pendientes.
    # V20.5: diagnóstico consultivo de reglas; no modifica estados ni historial.
    vista_solicitada = request.GET.get("vista")
    datos["vista"] = vista_solicitada if vista_solicitada in ("inventario", "reglas") else "pendientes"
    if datos["vista"] == "reglas":
        from dataclasses import astuple, is_dataclass
        from .evaluador_reglas import evaluar_etapa_expediente

        # Un único expediente por consulta: evita evaluar masivamente todas las etapas.
        expedientes_reglas = (ExpedienteMovilidad.objects.filter(activo=True)
                              .select_related("alumno", "convocatoria")
                              .order_by("alumno__username", "pk"))
        seleccionado = request.GET.get("expediente", "")
        if not seleccionado.isdecimal():
            seleccionado = ""
        datos["expedientes_reglas"] = expedientes_reglas
        datos["expediente_reglas_id"] = seleccionado
        datos["resultado_reglas"] = None
        datos["detalles_reglas"] = []
        datos["avisos_reglas"] = []
        datos["expediente_reglas"] = None
        datos["resultado_reglas_estado"] = ""
        if seleccionado:
            expediente_elegido = expedientes_reglas.filter(pk=int(seleccionado)).first()
            if expediente_elegido is not None:
                resultado = evaluar_etapa_expediente(expediente_elegido)
                # Adaptador explicito: utilizar los atributos de las dataclasses.
                # El sexto campo del resultado es informativo y no autoriza avance.
                valores = (
                    resultado.expediente_id,
                    resultado.etapa,
                    resultado.resultado,
                    resultado.detalles,
                    resultado.advertencias,
                )

                diagnostico = resultado.resultado
                detalles = []

                for d in resultado.detalles:
                    detalles.append({
                        "actividad_id": d.actividad_id,
                        "nombre": d.nombre,
                        "politica": d.politica,
                        "estado_actividad": d.estado_actividad,
                        "diagnostico": d.diagnostico,
                        "motivo": d.motivo,
                        "documentos": d.documentos_cargados,
                        "aprobados": d.documentos_aprobados,
                    })

                datos.update({
                    "expediente_reglas": expediente_elegido,
                    "resultado_reglas": resultado,
                    "resultado_reglas_estado": diagnostico,
                    "detalles_reglas": detalles,
                    "avisos_reglas": valores[4],
                })
                # No hacemos cambios a la base de datos desde esta vista.

    if datos["vista"] == "inventario":
        from .models import ActividadProceso

        opciones_responsable = list(ActividadProceso._meta.get_field("responsable").choices)
        opciones_etapa = list(ExpedienteMovilidad.Estado.choices)
        opciones_estado = list(ActividadExpediente._meta.get_field("estado").choices)

        responsable = request.GET.get("responsable", "")
        etapa = request.GET.get("etapa", "")
        estado = request.GET.get("estado", "")
        expediente_id = request.GET.get("expediente", "")
        if responsable not in {clave for clave, _ in opciones_responsable}:
            responsable = ""
        if etapa not in {clave for clave, _ in opciones_etapa}:
            etapa = ""
        if estado not in {clave for clave, _ in opciones_estado}:
            estado = ""
        if not expediente_id.isdecimal():
            expediente_id = ""

        inventario = (ActividadExpediente.objects
            .filter(expediente__activo=True)
            .select_related("expediente__alumno", "actividad_proceso")
            .order_by("expediente_id", "actividad_proceso__orden", "pk"))
        if responsable:
            inventario = inventario.filter(actividad_proceso__responsable=responsable)
        if etapa:
            inventario = inventario.filter(actividad_proceso__estado_expediente=etapa)
        if estado:
            inventario = inventario.filter(estado=estado)
        if expediente_id:
            inventario = inventario.filter(expediente_id=int(expediente_id))

        grupos_inventario = []
        ultimo_id = None
        for registro in inventario:
            if registro.expediente_id != ultimo_id:
                grupos_inventario.append({"expediente": registro.expediente, "actividades": []})
                ultimo_id = registro.expediente_id
            grupos_inventario[-1]["actividades"].append(registro)

        datos.update({
            "grupos_inventario": grupos_inventario,
            "total_inventario": sum(len(g["actividades"]) for g in grupos_inventario),
            "opciones_responsable": opciones_responsable,
            "opciones_etapa": opciones_etapa,
            "opciones_estado": opciones_estado,
            "filtro_responsable": responsable,
            "filtro_etapa": etapa,
            "filtro_estado": estado,
            "filtro_expediente": expediente_id,
            "expedientes_filtro": ExpedienteMovilidad.objects.filter(activo=True)
                .select_related("alumno").order_by("alumno__username", "pk"),
        })
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


@login_required
def inventario_documental_responsable(request, pk):
    """Inventario global del expediente, fuera de las estaciones del recorrido."""
    if not es_responsable_autorizado(request.user):
        raise PermissionDenied("No tiene permiso para consultar expedientes ajenos.")
    if not request.user.has_perm("expedientes.view_documentoexpediente"):
        raise PermissionDenied("No tiene permiso para consultar documentos.")

    expediente = get_object_or_404(
        ExpedienteMovilidad.objects.select_related("alumno", "convocatoria"),
        pk=pk,
    )
    documentos_historicos = (
        DocumentoExpediente.objects.filter(
            expediente=expediente, actividad__isnull=True
        ).order_by("pk")
    )
    documentos_vinculados = (
        DocumentoExpediente.objects.filter(
            expediente=expediente, actividad__isnull=False
        ).select_related("actividad__actividad_proceso").order_by("pk")
    )
    actividades_vinculables = (
        ActividadExpediente.objects.filter(expediente=expediente)
        .select_related("actividad_proceso").order_by("pk")
    )
    return render(request, "expedientes/inventario_documental.html", {
        "expediente": expediente,
        "puede_ver_documentos": True,
        "documentos_historicos": documentos_historicos,
        "documentos_vinculados": documentos_vinculados,
        "actividades_vinculables": actividades_vinculables,
    })
