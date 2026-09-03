from django.contrib import admin

# Register your models here.


from .models import (
    Convocatoria,
    ConvocatoriaIES,
    FechaImportante,
    IES,
    Requisito,
    TipoMovilidad,
)


@admin.register(TipoMovilidad)
class TipoMovilidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "orden")
    list_editable = ("activo", "orden")
    search_fields = ("nombre",)
    ordering = ("orden", "nombre")


class RequisitoInline(admin.TabularInline):
    model = Requisito
    extra = 1
    fields = ("texto", "obligatorio", "activo", "orden")


class FechaImportanteInline(admin.TabularInline):
    model = FechaImportante
    extra = 1
    fields = (
        "titulo",
        "fecha",
        "hora",
        "es_fecha_limite",
        "activa",
        "orden",
    )


class ConvocatoriaIESInline(admin.TabularInline):
    model = ConvocatoriaIES
    extra = 1
    autocomplete_fields = ("ies",)
    fields = (
        "ies",
        "disponible",
        "observaciones",
        "restricciones",
        "orden",
    )


@admin.register(Convocatoria)
class ConvocatoriaAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "tipo_movilidad",
        "ciclo",
        "anio",
        "estado",
        "destacada",
        "fecha_publicacion",
    )

    list_filter = (
        "tipo_movilidad",
        "ciclo",
        "anio",
        "estado",
        "destacada",
    )

    search_fields = (
        "titulo",
        "resumen",
        "descripcion",
    )

    ordering = ("-anio", "ciclo", "titulo")

    inlines = (
        RequisitoInline,
        FechaImportanteInline,
        ConvocatoriaIESInline,
    )


@admin.register(IES)
class IESAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "pais",
        "estado_region",
        "activa",
    )

    list_filter = (
        "pais",
        "activa",
    )

    search_fields = (
        "nombre",
        "pais",
        "estado_region",
    )

    ordering = (
        "pais",
        "nombre",
    )


@admin.register(Requisito)
class RequisitoAdmin(admin.ModelAdmin):
    list_display = (
        "convocatoria",
        "texto_corto",
        "obligatorio",
        "activo",
        "orden",
    )

    list_filter = (
        "obligatorio",
        "activo",
        "convocatoria",
    )

    def texto_corto(self, obj):
        return obj.texto[:80]

    texto_corto.short_description = "Requisito"


@admin.register(FechaImportante)
class FechaImportanteAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "convocatoria",
        "fecha",
        "hora",
        "es_fecha_limite",
        "activa",
    )

    list_filter = (
        "es_fecha_limite",
        "activa",
        "convocatoria",
    )

    date_hierarchy = "fecha"


@admin.register(ConvocatoriaIES)
class ConvocatoriaIESAdmin(admin.ModelAdmin):
    list_display = (
        "convocatoria",
        "ies",
        "disponible",
        "orden",
    )

    list_filter = (
        "disponible",
        "convocatoria",
    )

    autocomplete_fields = ("ies",)