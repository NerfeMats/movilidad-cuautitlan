from django.urls import path

from . import views


app_name = "convocatorias"


urlpatterns = [
    path(
        "",
        views.lista_convocatorias,
        name="lista",
    ),
    path(
        "<int:pk>/",
        views.detalle_convocatoria,
        name="detalle",
    ),
]