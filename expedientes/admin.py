from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError

from .models import (
    ExpedienteMovilidad,
    ActividadProceso,
    ActividadExpediente,
    DocumentoExpediente,
    HistorialExpediente,
)



class ExpedienteAltaAdminForm(forms.ModelForm):
    """Evita contradicciones al registrar expedientes ya iniciados."""

    class Meta:
        model = ExpedienteMovilidad
        fields = "__all__"

    def clean(self):
        data = super().clean()
        if self.instance.pk is None:
            inicial = data.get("estado_inicial")
            tipo = data.get("tipo_alta")
            if "estado" in self.fields:
                # Mantiene las validaciones previas en formularios que
                # explicitamente incluyen estado (tambien en pruebas 16).
                actual = data.get("estado")
                if tipo == ExpedienteMovilidad.TipoAlta.NORMAL and actual != ExpedienteMovilidad.Estado.INICIADO:
                    self.add_error("estado", "El alta normal debe iniciar en Iniciado.")
                if tipo == ExpedienteMovilidad.TipoAlta.EXCEPCIONAL and inicial and actual != inicial:
                    self.add_error("estado", "En una incorporación excepcional el estado actual debe coincidir con el estado inicial declarado.")
            elif inicial:
                # En Django Admin el campo estado se omite durante el alta.
                self.instance.estado = inicial
        return data

    def save(self, commit=True):
        # Asignacion en servidor incluso si se invoca save() sin clean().
        # En ediciones, el estado evoluciona exclusivamente por el flujo.
        if self.instance.pk is None:
            inicial = self.cleaned_data.get("estado_inicial")
            if inicial:
                self.instance.estado = inicial
        return super().save(commit=commit)

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
        "fecha_cumplimiento_real",
        "observaciones",
    )

    readonly_fields = (
        "actividad_proceso",
        "fecha_completada",
    )


@admin.register(ExpedienteMovilidad)
class ExpedienteMovilidadAdmin(admin.ModelAdmin):
    form = ExpedienteAltaAdminForm
    # Avances masivos deshabilitados hasta validar las reglas institucionales.
    actions = []

    fieldsets = (
        ("Identificación", {"fields": ("alumno", "convocatoria", "ies_destino", "activo")}),
        ("Situación al registrar", {"fields": (
            "tipo_alta", "origen", "estado_inicial", "estado",
            "motivo_alta_excepcional", "observaciones",
        )}),
        ("Fechas: registro digital y hechos acreditados", {"fields": (
            "fecha_inicio", "fecha_recepcion_area", "fecha_inicio_real_movilidad",
            "fecha_actualizacion", "fecha_cierre",
        )}),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is not None:
            return fieldsets
        # Quitar el selector redundante solo durante el alta.
        return tuple(
            (
                titulo,
                {**opciones, "fields": tuple(
                    campo for campo in opciones["fields"]
                    if campo != "estado"
                )},
            )
            for titulo, opciones in fieldsets
        )

    def get_exclude(self, request, obj=None):
        excluidos = tuple(super().get_exclude(request, obj) or ())
        if obj is None:
            return tuple(dict.fromkeys((*excluidos, "estado")))
        return excluidos or None

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

        fecha_anterior = None
        if change and "fecha_inicio_real_movilidad" in form.changed_data:
            fecha_anterior = ExpedienteMovilidad.objects.only(
                "fecha_inicio_real_movilidad"
            ).get(pk=obj.pk).fecha_inicio_real_movilidad

        super().save_model(request, obj, form, change)

        if change and "fecha_inicio_real_movilidad" in form.changed_data:
            HistorialExpediente.objects.create(
                expediente=obj,
                usuario=request.user,
                accion="Corrección de fecha de inicio real",
                descripcion=(
                    f"Fecha real de inicio de movilidad: {fecha_anterior or 'sin dato'} "
                    f"-> {obj.fecha_inicio_real_movilidad or 'sin dato'}"
                ),
                estado_anterior=obj.estado,
                estado_nuevo=obj.estado,
            )

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