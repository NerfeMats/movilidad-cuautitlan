from django.urls import path

from . import views


app_name = "expedientes"


urlpatterns = [
    path(
        "",
        views.lista_expedientes,
        name="lista",
    ),
    path(
        "<int:pk>/",
        views.detalle_expediente,
        name="detalle",
    ),
]

