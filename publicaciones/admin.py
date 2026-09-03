from django.contrib import admin

# Register your models here.


from .models import (
    CategoriaFAQ,
    PreguntaFrecuente,
    Publicacion,
)


@admin.register(CategoriaFAQ)
class CategoriaFAQAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "activa",
        "orden",
    )

    list_editable = (
        "activa",
        "orden",
    )

    search_fields = ("nombre",)


@admin.register(Publicacion)
class PublicacionAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "categoria",
        "publicada",
        "destacada",
        "fecha_publicacion",
        "fecha_fin",
    )

    list_filter = (
        "categoria",
        "publicada",
        "destacada",
        "tipo_movilidad",
    )

    search_fields = (
        "titulo",
        "contenido",
    )

    autocomplete_fields = (
        "convocatoria",
        "tipo_movilidad",
    )

    ordering = (
        "-fecha_publicacion",
        "-creado_en",
    )


@admin.register(PreguntaFrecuente)
class PreguntaFrecuenteAdmin(admin.ModelAdmin):
    list_display = (
        "pregunta",
        "categoria",
        "tipo_movilidad",
        "publicada",
        "orden",
    )

    list_filter = (
        "categoria",
        "tipo_movilidad",
        "publicada",
    )

    search_fields = (
        "pregunta",
        "respuesta",
    )

    ordering = (
        "categoria",
        "orden",
    )