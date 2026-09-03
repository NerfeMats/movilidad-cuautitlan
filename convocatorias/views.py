from django.shortcuts import render, get_object_or_404
# Create your views here.


from .models import Convocatoria


def lista_convocatorias(request):
    convocatorias = Convocatoria.objects.filter(
        estado=Convocatoria.Estado.PUBLICADA
    )

    return render(
        request,
        "convocatorias/lista.html",
        {
            "convocatorias": convocatorias,
        },
    )


def detalle_convocatoria(request, pk):
    convocatoria = get_object_or_404(
        Convocatoria,
        pk=pk,
        estado=Convocatoria.Estado.PUBLICADA,
    )

    return render(
        request,
        "convocatorias/detalle.html",
        {
            "convocatoria": convocatoria,
        },
    )