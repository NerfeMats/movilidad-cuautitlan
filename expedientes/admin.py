from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import (
    ExpedienteMovilidad,
    ActividadProceso,
    ActividadExpediente,
    DocumentoExpediente,
    HistorialExpediente,
)


class ActividadExpedienteInline(admin.TabularInline):
    model = ActividadExpediente
    extra = 0
    can_delete = False

    fields = (
        "actividad_proceso",
        "estado",
        "fecha_limite",
        "fecha_completada",
        "observaciones",
    )

    readonly_fields = (
        "actividad_proceso",
    )


@admin.register(ExpedienteMovilidad)
class ExpedienteMovilidadAdmin(admin.ModelAdmin):

    list_display = (
    "alumno",
    "convocatoria",
    "estado",
    "tipo_alta",
    "origen",
    "fecha_inicio",
    "listo_para_avanzar",
)

    list_filter = (
        "estado",
        "tipo_alta",
        "origen",
        "convocatoria",
    )

    search_fields = (
        "alumno__username",
        "alumno__first_name",
        "alumno__last_name",
    )
    inlines = [
        ActividadExpedienteInline,
        ]
    def save_model(self, request, obj, form, change):
        es_nuevo = obj.pk is None

        super().save_model(request, obj, form, change)

        if es_nuevo:
            obj.crear_actividades_iniciales()
    
    @admin.display(
    boolean=True,
    description="Listo para avanzar",
)
    def listo_para_avanzar(self, obj):
        return obj.puede_avanzar()

    actions = [
    "avanzar_estado_seleccionados",
    ]

    @admin.action(description="Avanzar estado de los expedientes seleccionados")
    def avanzar_estado_seleccionados(self, request, queryset):

        avanzados = 0
        no_avanzados = 0

        for expediente in queryset:

            if expediente.avanzar_estado(usuario=request.user):
                avanzados += 1
            else:
                no_avanzados += 1

        if avanzados:
            self.message_user(
                request,
                f"{avanzados} expediente(s) avanzaron de estado.",
                level="SUCCESS",
            )

        if no_avanzados:
            self.message_user(
                request,
                f"{no_avanzados} expediente(s) no pudieron avanzar.",
                level="WARNING",
            )

@admin.register(ActividadProceso)
class ActividadProcesoAdmin(admin.ModelAdmin):

    list_display = (
        "nombre",
        "tipo_movilidad",
        "estado_expediente",
        "etapa",
        "responsable",
        "orden",
        "activo",
    )

    list_filter = (
        "tipo_movilidad",
        "etapa",
        "responsable",
        "activo",
    )

    list_editable = (
        "orden",
        "activo",
    )


@admin.register(ActividadExpediente)
class ActividadExpedienteAdmin(admin.ModelAdmin):

    list_display = (
        "expediente",
        "actividad_proceso",
        "estado",
        "fecha_limite",
    )

    list_filter = (
        "estado",
    )



admin.site.register(DocumentoExpediente)
admin.site.register(HistorialExpediente)