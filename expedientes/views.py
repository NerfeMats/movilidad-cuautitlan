from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

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

    contexto = {
        "expedientes": expedientes,
    }

    return render(
        request,
        "expedientes/lista_expedientes.html",
        contexto,
    )

@login_required
def detalle_expediente(request, pk):

    expediente = get_object_or_404(
        ExpedienteMovilidad.objects
        .select_related(
            "convocatoria",
            "convocatoria__tipo_movilidad",
            "ies_destino",
        )
        .prefetch_related(
            "actividades__actividad_proceso",
        ),
        pk=pk,
        alumno=request.user,
    )

    actividades = expediente.actividades.all()

    contexto = {
        "expediente": expediente,
        "actividades": actividades,
    }

    return render(
        request,
        "expedientes/detalle_expediente.html",
        contexto,
    )