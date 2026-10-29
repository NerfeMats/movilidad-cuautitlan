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


# Panel del responsable de movilidad
from . import panel_responsable

urlpatterns += [
    path("responsable/", panel_responsable.panel_responsable, name="panel_responsable"),
    path("responsable/<int:pk>/", panel_responsable.ruta_responsable, name="ruta_responsable"),
]
