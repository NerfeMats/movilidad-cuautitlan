from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import DocumentoExpediente, ActividadExpediente
from .seguimiento_servicio import vincular_documento


@login_required
@require_POST
def vincular_documento_web(request, documento_id):
    if not request.user.is_active or not request.user.is_staff or not request.user.has_perm("expedientes.change_documentoexpediente"):
        raise PermissionDenied("Sin permiso de vinculación")
    documento = get_object_or_404(DocumentoExpediente, pk=documento_id)
    destino = "expedientes:ruta_responsable"
    valor = request.POST.get("actividad_id", "").strip()
    if valor:
        try:
            pk = int(valor)
        except ValueError:
            raise Http404("Actividad inválida")
        actividad = get_object_or_404(ActividadExpediente, pk=pk, expediente_id=documento.expediente_id)
        valor = actividad.pk
    else:
        valor = None
    try:
        _, cambio = vincular_documento(usuario=request.user, documento_id=documento.pk, actividad_id=valor)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        if cambio:
            messages.success(request, "Vinculación registrada sin aprobar documentos ni actividades.")
        else:
            messages.info(request, "El documento ya tenía esa vinculación.")
    return redirect(destino, pk=documento.expediente_id)
