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

# Acceso documental: protegido en el servicio para cada acción.
from . import documentos_web

urlpatterns += [
    path("documentos/actividad/<int:actividad_id>/cargar/", documentos_web.cargar_documento_web, name="documento_cargar"),
    path("documentos/<int:documento_id>/descargar/", documentos_web.descargar_documento_web, name="documento_descargar"),
    path("documentos/<int:documento_id>/revisar/", documentos_web.revisar_documento_web, name="documento_revisar"),
]

# V19: centro global y bandeja privada de alumno.
urlpatterns += [
    path("responsable/seguimiento/", panel_responsable.centro_seguimiento, name="centro_seguimiento"),
    path("mis-pendientes/", panel_responsable.mis_pendientes, name="mis_pendientes"),
]
from . import seguimiento_web
urlpatterns += [
    path("documentos/<int:documento_id>/vincular/", seguimiento_web.vincular_documento_web, name="documento_vincular"),
]
