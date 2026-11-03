"""Reglas de movilidad configurables: fase 2 (sin activar los bloqueos).

No modifica la lógica actual de puede_avanzar() ni las actividades históricas.
"""
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.conf import settings


class PoliticaRegla(models.TextChoices):
    BLOQUEANTE = "BLOQUEANTE", "Bloqueante"
    CONDICIONAL = "CONDICIONAL", "Condicional"
    SEGUIMIENTO = "SEGUIMIENTO", "Seguimiento"


class EstadoConfiguracion(models.TextChoices):
    SIN_DEFINIR = "SIN_DEFINIR", "Sin definir"
    DEFINIDA = "DEFINIDA", "Definida"


class ReglaActividadConvocatoria(models.Model):
    """Configuración explícita, exclusiva de una convocatoria y actividad.

    SIN_DEFINIR no equivale a SEGUIMIENTO. Solo reglas DEFINIDA pueden
    congelarse sobre un expediente, mediante una operación explícita.
    """
    convocatoria = models.ForeignKey(
        "convocatorias.Convocatoria", on_delete=models.PROTECT,
        related_name="reglas_actividades",
    )
    actividad_proceso = models.ForeignKey(
        "expedientes.ActividadProceso", on_delete=models.PROTECT,
        related_name="reglas_convocatorias",
    )
    estado_configuracion = models.CharField(
        max_length=20, choices=EstadoConfiguracion.choices,
        default=EstadoConfiguracion.SIN_DEFINIR,
    )
    politica = models.CharField(
        max_length=20, choices=PoliticaRegla.choices,
        default=PoliticaRegla.SEGUIMIENTO,
    )
    condicion_aplicabilidad = models.TextField(blank=True)
    fundamento = models.TextField(blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Regla de actividad de convocatoria"
        verbose_name_plural = "Reglas de actividades de convocatoria"
        constraints = [
            models.UniqueConstraint(
                fields=["convocatoria", "actividad_proceso"],
                name="regla_unica_convocatoria_actividad",
            )
        ]

    def clean(self):
        super().clean()
        errores = {}
        if self.convocatoria_id and self.actividad_proceso_id:
            if self.convocatoria.tipo_movilidad_id != self.actividad_proceso.tipo_movilidad_id:
                errores["actividad_proceso"] = "La actividad no pertenece al tipo de movilidad de la convocatoria."
        if self.estado_configuracion == EstadoConfiguracion.DEFINIDA:
            if not self.fundamento.strip():
                errores["fundamento"] = "Documente el fundamento de la regla definida."
            if self.politica == PoliticaRegla.CONDICIONAL and not self.condicion_aplicabilidad.strip():
                errores["condicion_aplicabilidad"] = "La regla condicional requiere una condición explícita."
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f"{self.convocatoria} / {self.actividad_proceso}"


class ReglaActividadExpediente(models.Model):
    """Copia estática de la política aplicable a una actividad individual.

    La copia no se actualiza cuando cambia el catálogo o la convocatoria.
    Esta fase no la consulta para autorizar el avance.
    """
    class Aplicabilidad(models.TextChoices):
        SIN_RESOLVER = "SIN_RESOLVER", "Sin resolver"
        APLICA = "APLICA", "Aplica"
        NO_APLICA = "NO_APLICA", "No aplica"

    actividad_expediente = models.OneToOneField(
        "expedientes.ActividadExpediente", on_delete=models.CASCADE,
        related_name="regla_asignada",
    )
    regla_origen = models.ForeignKey(
        ReglaActividadConvocatoria, on_delete=models.PROTECT,
        related_name="copias_expedientes",
    )
    politica = models.CharField(max_length=20, choices=PoliticaRegla.choices)
    condicion_aplicabilidad = models.TextField(blank=True)
    fundamento = models.TextField(blank=True)
    aplicabilidad = models.CharField(
        max_length=20, choices=Aplicabilidad.choices,
        default=Aplicabilidad.SIN_RESOLVER,
    )
    justificacion_no_aplica = models.TextField(blank=True)
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="reglas_movilidad_validadas",
    )
    validado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Regla asignada a actividad de expediente"
        verbose_name_plural = "Reglas asignadas a actividades de expedientes"

    def clean(self):
        super().clean()
        errores = {}
        if self.regla_origen_id and self.actividad_expediente_id:
            actividad = self.actividad_expediente
            regla = self.regla_origen
            if actividad.expediente.convocatoria_id != regla.convocatoria_id:
                errores["regla_origen"] = "La regla pertenece a otra convocatoria."
            if actividad.actividad_proceso_id != regla.actividad_proceso_id:
                errores["regla_origen"] = "La regla pertenece a otra actividad."
        if self.aplicabilidad == self.Aplicabilidad.NO_APLICA:
            if not self.justificacion_no_aplica.strip():
                errores["justificacion_no_aplica"] = "La no aplicabilidad requiere justificación."
            if not self.validado_por_id or not self.validado_en:
                errores["validado_por"] = "La no aplicabilidad debe estar validada y fechada."
        if bool(self.validado_por_id) != bool(self.validado_en):
            errores["validado_en"] = "El validador y la fecha deben registrarse juntos."
        if errores:
            raise ValidationError(errores)

    @classmethod
    def crear_copia(cls, actividad_expediente, regla):
        """Asignación explícita: NO se invoca durante migraciones ni altas.

        No cambia el estado ni la lógica de avance del expediente.
        """
        if regla.estado_configuracion != EstadoConfiguracion.DEFINIDA:
            raise ValidationError("La regla de convocatoria aún no está definida.")
        regla.full_clean()
        with transaction.atomic():
            copia = cls(
                actividad_expediente=actividad_expediente,
                regla_origen=regla,
                politica=regla.politica,
                condicion_aplicabilidad=regla.condicion_aplicabilidad,
                fundamento=regla.fundamento,
            )
            copia.full_clean()
            copia.save(force_insert=True)
        return copia

    def __str__(self):
        return f"{self.actividad_expediente_id}: {self.get_politica_display()}"
