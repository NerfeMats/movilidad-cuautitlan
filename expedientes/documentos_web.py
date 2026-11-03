"""HTTP documental: únicamente utiliza el servicio privado 15A."""
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .documentos_servicio import abrir_documento, cargar_documento, revisar_documento
from .models import ActividadExpediente, DocumentoExpediente


def _volver(usuario, expediente):
    if usuario.pk == expediente.alumno_id:
        return reverse("expedientes:detalle", args=[expediente.pk])
    return reverse("expedientes:ruta_responsable", args=[expediente.pk])


@login_required
@require_POST
def cargar_documento_web(request, actividad_id):
    actividad = get_object_or_404(
        ActividadExpediente.objects.select_related("expediente", "actividad_proceso"),
        pk=actividad_id,
    )
    # El servicio aplica la autorización a cada solicitud, no el formulario.
    destino = _volver(request.user, actividad.expediente)
    archivo = request.FILES.get("archivo")
    if archivo is None:
        messages.error(request, "Selecciona un archivo para adjuntar.")
        return redirect(destino)
    try:
        cargar_documento(
            usuario=request.user,
            actividad=actividad,
            archivo=archivo,
            nombre=request.POST.get("nombre", ""),
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "Documento recibido; pendiente de revisión.")
    return redirect(destino)


@login_required
@require_GET
def descargar_documento_web(request, documento_id):
    documento = get_object_or_404(DocumentoExpediente, pk=documento_id)
    try:
        archivo = abrir_documento(usuario=request.user, documento=documento)
    except ValidationError as error:
        raise Http404("Documento no disponible en el almacenamiento privado") from error
    # FileResponse cierra el archivo tras completar la respuesta.
    nombre = Path(getattr(documento, "nombre_archivo_original", "") or documento.nombre).name.strip() or "evidencia"
    extension = Path(documento.archivo.name).suffix.lower()
    if not nombre.lower().endswith(extension):
        nombre += extension
    respuesta = FileResponse(archivo, as_attachment=True, filename=nombre,
                             content_type="application/octet-stream")
    respuesta["Cache-Control"] = "private, no-store"
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta


@login_required
@require_POST
def revisar_documento_web(request, documento_id):
    documento = get_object_or_404(
        DocumentoExpediente.objects.select_related("expediente"), pk=documento_id
    )
    accion = request.POST.get("decision")
    if accion not in ("aprobar", "corregir"):
        messages.error(request, "Selecciona una decisión válida.")
        return redirect(_volver(request.user, documento.expediente))
    try:
        revisar_documento(
            usuario=request.user,
            documento=documento,
            aprobar=(accion == "aprobar"),
            observaciones=request.POST.get("observaciones", ""),
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "Revisión documental registrada.")
    return redirect(_volver(request.user, documento.expediente))
