from django.contrib import admin
from django import forms
# Register your models here.
from django.contrib import admin

from .models import (
    ExpedienteMovilidad,
    ActividadProceso,
    ActividadExpediente,
    DocumentoExpediente,
    HistorialExpediente,
)

class ActividadExpedienteAdminForm(forms.ModelForm):

    class Meta:
        model = ActividadExpediente
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        actividad = self.instance

        if (
            actividad
            and actividad.pk
            and actividad.expediente_id
            and actividad.actividad_proceso_id
        ):
            etapa_actividad = (
                actividad.actividad_proceso.estado_expediente
            )

            etapa_actual = actividad.expediente.estado

            if etapa_actividad != etapa_actual:

                for campo in (
                    "estado",
                    "fecha_limite",
                    "observaciones",
                ):
                    if campo in self.fields:
                        self.fields[campo].disabled = True
class ActividadExpedienteInline(admin.TabularInline):

    model = ActividadExpediente
    form = ActividadExpedienteAdminForm

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
        "fecha_completada",
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

            HistorialExpediente.objects.create(
                expediente=obj,
                usuario=request.user,
                accion="Creación de expediente",
                descripcion=(
                    f"Se creó el expediente en estado "
                    f"{obj.get_estado_display()}."
                ),
                estado_anterior="",
                estado_nuevo=obj.estado,
            )
    
    @admin.display(
    boolean=True,
    description="Listo para avanzar",
     )
    def listo_para_avanzar(self, obj):
        return obj.puede_avanzar()

    actions = [
    "avanzar_estado_seleccionados",
    ]

    def get_readonly_fields(self, request, obj=None):

        if obj:
            return (
                "estado",
                "tipo_alta",
                "estado_inicial",
                "origen",
                "fecha_inicio",
                "fecha_actualizacion",
                "fecha_cierre",
            )

        return (
            "fecha_inicio",
            "fecha_actualizacion",
            "fecha_cierre",
        )

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

    form = ActividadExpedienteAdminForm

    list_display = (
        "expediente",
        "actividad_proceso",
        "estado",
        "fecha_limite",
    )

    list_filter = (
        "estado",
    )

    readonly_fields = (
        "actividad_proceso",
        "expediente",
        "fecha_completada",
    )



admin.site.register(DocumentoExpediente)
@admin.register(HistorialExpediente)
class HistorialExpedienteAdmin(admin.ModelAdmin):

    list_display = (
        "expediente",
        "usuario",
        "accion",
        "estado_anterior",
        "estado_nuevo",
        "fecha",
    )

    list_filter = (
        "accion",
        "estado_anterior",
        "estado_nuevo",
        "fecha",
    )

    search_fields = (
        "expediente__alumno__username",
        "expediente__alumno__first_name",
        "expediente__alumno__last_name",
        "accion",
        "descripcion",
    )

    readonly_fields = (
        "expediente",
        "usuario",
        "accion",
        "descripcion",
        "estado_anterior",
        "estado_nuevo",
        "fecha",
    )

    ordering = (
        "-fecha",
    )
    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False