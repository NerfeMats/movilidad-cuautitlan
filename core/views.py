from django.shortcuts import render

from convocatorias.models import Convocatoria
from publicaciones.models import PreguntaFrecuente
# Create your views here.



def inicio(request):
    convocatorias = Convocatoria.objects.filter(
        estado=Convocatoria.Estado.PUBLICADA
    ).order_by(
        "-destacada",
        "-anio",
        "ciclo",
    )

    preguntas_frecuentes = (
        PreguntaFrecuente.objects
        .filter(publicada=True)
        .select_related("categoria", "tipo_movilidad")
        .order_by(
            "categoria__orden",
            "orden",
            "pregunta",
        )[:5]
    )


    contexto = {
        "convocatorias": convocatorias,
        "preguntas_frecuentes": preguntas_frecuentes,
    }

    return render(
        request,
        "core/inicio.html",
        contexto,
    )