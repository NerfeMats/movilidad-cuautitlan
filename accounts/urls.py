from django.urls import path
from .views import AccesoMovilidad, SalidaMovilidad

app_name = "accounts"
urlpatterns = [
    path("login/", AccesoMovilidad.as_view(), name="login"),
    path("logout/", SalidaMovilidad.as_view(), name="logout"),
]
