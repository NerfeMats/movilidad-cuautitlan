"""Gestiones documentales auditadas: nunca cambian estado de actividad."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import DocumentoExpediente, ActividadExpediente, HistorialExpediente


@transaction.atomic
def vincular_documento(*, usuario, documento_id, actividad_id=None):
    if not getattr(usuario, "is_authenticated", False) or not usuario.is_active or not usuario.is_staff or not usuario.has_perm("expedientes.change_documentoexpediente"):
        raise PermissionDenied("Se requiere permiso para vinculación documental")
    doc = DocumentoExpediente.objects.select_for_update().select_related("expediente").get(pk=documento_id)
    if doc.visibilidad != DocumentoExpediente.Visibilidad.RESPONSABLE:
        raise ValidationError("La operación se limita a documentos administrativos reservados")
    if actividad_id is not None:
        actividad = ActividadExpediente.objects.get(pk=actividad_id)
        if actividad.expediente_id != doc.expediente_id:
            raise ValidationError("Documento y actividad deben pertenecer al mismo expediente")
    else:
        actividad = None
    anterior = doc.actividad_id
    nuevo = actividad.pk if actividad else None
    if anterior == nuevo:
        return doc, False
    doc.actividad = actividad
    doc.save(update_fields=["actividad"])
    HistorialExpediente.objects.create(
        expediente=doc.expediente, usuario=usuario,
        accion="DOCUMENTO_VINCULADO" if nuevo else "DOCUMENTO_DESVINCULADO",
        descripcion=f"Documento {doc.pk}: actividad anterior {anterior}; nueva {nuevo}. Sin aprobación de actividad ni documento.",
        estado_anterior=doc.expediente.estado,
        estado_nuevo=doc.expediente.estado,
    )
    return doc, True
