from django.db import models

# Create your models here.
from django.conf import settings
from django.utils import timezone
from convocatorias.models import (
    Convocatoria,
    ConvocatoriaIES,
    TipoMovilidad,
)
from django.core.exceptions import ValidationError

class ExpedienteMovilidad(models.Model):

    class Estado(models.TextChoices):
        INICIADO = "INICIADO", "Iniciado"

        INTEGRANDO_EXPEDIENTE = (
            "INTEGRANDO_EXPEDIENTE",
            "Integrando expediente",
        )

        EN_REVISION = (
            "EN_REVISION",
            "En revisión",
        )

        ENVIADO_DAAE = (
            "ENVIADO_DAAE",
            "Enviado a DAAE",
        )

        POSTULACION_IES = (
            "POSTULACION_IES",
            "Postulación ante IES",
        )

        PREPARACION_MOVILIDAD = (
            "PREPARACION_MOVILIDAD",
            "Preparación de movilidad",
        )

        EN_MOVILIDAD = (
            "EN_MOVILIDAD",
            "En movilidad",
        )

        HOMOLOGACION = (
            "HOMOLOGACION",
            "En proceso de homologación",
        )

        CERRADO = (
            "CERRADO",
            "Cerrado",
        )

        CANCELADO = (
            "CANCELADO",
            "Cancelado",
        )

    class TipoAlta(models.TextChoices):
        NORMAL = "NORMAL", "Alta normal"

        EXCEPCIONAL = (
            "EXCEPCIONAL",
            "Expediente recibido en curso",
        )

    class Origen(models.TextChoices):
        NUEVO = "NUEVO", "Nuevo"

        GESTION_ANTERIOR = (
            "GESTION_ANTERIOR",
            "Recibido de gestión anterior",
        )

        REGISTRO_PREVIO = (
            "REGISTRO_PREVIO",
            "Migrado de registro previo",
        )

        OTRO = "OTRO", "Otro"

    ORDEN_ESTADOS = {
        Estado.INICIADO: 1,
        Estado.INTEGRANDO_EXPEDIENTE: 2,
        Estado.EN_REVISION: 3,
        Estado.ENVIADO_DAAE: 4,
        Estado.POSTULACION_IES: 5,
        Estado.PREPARACION_MOVILIDAD: 6,
        Estado.EN_MOVILIDAD: 7,
        Estado.HOMOLOGACION: 8,
        Estado.CERRADO: 9,
    }
    alumno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="expedientes_movilidad",
    )

    convocatoria = models.ForeignKey(
        Convocatoria,
        on_delete=models.PROTECT,
        related_name="expedientes",
    )

    ies_destino = models.ForeignKey(
        ConvocatoriaIES,
        on_delete=models.PROTECT,
        related_name="expedientes",
        null=True,
        blank=True,
    )

    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.INICIADO,
    )

    tipo_alta = models.CharField(
        max_length=20,
        choices=TipoAlta.choices,
        default=TipoAlta.NORMAL,
    )

    estado_inicial = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.INICIADO,
    )

    origen = models.CharField(
        max_length=30,
        choices=Origen.choices,
        default=Origen.NUEVO,
    )

    fecha_inicio = models.DateTimeField(
        auto_now_add=True,
    )

    fecha_recepcion_area = models.DateField(
        null=True,
        blank=True,
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
    )

    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
    )

    motivo_alta_excepcional = models.TextField(
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["-fecha_inicio"]

        constraints = [
            models.UniqueConstraint(
                fields=["alumno", "convocatoria"],
                name="expediente_unico_alumno_convocatoria",
            )
        ]

        verbose_name = "Expediente de movilidad"
        verbose_name_plural = "Expedientes de movilidad"

    def __str__(self):
        return (
            f"{self.alumno} - "
            f"{self.convocatoria} - "
            f"{self.get_estado_display()}"
        )

    def clean(self):
        errors = {}

        if self.tipo_alta == self.TipoAlta.NORMAL:
            if self.estado_inicial != self.Estado.INICIADO:
                errors["estado_inicial"] = (
                    "Un expediente de alta normal debe iniciar "
                    "en el estado 'Iniciado'."
                )

        if self.tipo_alta == self.TipoAlta.EXCEPCIONAL:
            if self.estado_inicial == self.Estado.INICIADO:
                errors["estado_inicial"] = (
                    "En un expediente recibido en curso debe indicar "
                    "el estado real en el que fue recibido."
                )

            if not self.motivo_alta_excepcional:
                errors["motivo_alta_excepcional"] = (
                    "Debe indicar el motivo del alta excepcional."
                )

            if not self.fecha_recepcion_area:
                errors["fecha_recepcion_area"] = (
                    "Debe indicar la fecha en que el expediente "
                    "fue recibido por el área."
                )

        if errors:
            raise ValidationError(errors)

    def crear_actividades_iniciales(self):

        actividades = ActividadProceso.objects.filter(
            tipo_movilidad=self.convocatoria.tipo_movilidad,
            activo=True,
        )

        orden_inicial = self.ORDEN_ESTADOS.get(
            self.estado_inicial,
            1,
        )

        for actividad in actividades:

            if self.tipo_alta == self.TipoAlta.NORMAL:

                estado_actividad = (
                    ActividadExpediente.Estado.PENDIENTE
                )

            else:

                orden_actividad = self.ORDEN_ESTADOS.get(
                    actividad.estado_expediente,
                    1,
                )

                if orden_actividad < orden_inicial:
                    estado_actividad = (
                        ActividadExpediente.Estado.NO_REGISTRADA
                    )
                else:
                    estado_actividad = (
                        ActividadExpediente.Estado.PENDIENTE
                    )

            ActividadExpediente.objects.get_or_create(
                expediente=self,
                actividad_proceso=actividad,
                defaults={
                    "estado": estado_actividad,
                },
            )
  
class ActividadProceso(models.Model):

    class Etapa(models.TextChoices):
        ANTES = "ANTES", "Antes de la movilidad"
        DURANTE = "DURANTE", "Durante la movilidad"
        DESPUES = "DESPUES", "Después de la movilidad"

    class Responsable(models.TextChoices):
        ALUMNO = "ALUMNO", "Alumno"

        RESPONSABLE_MOVILIDAD = (
            "RESPONSABLE_MOVILIDAD",
            "Responsable de movilidad",
        )

        ESPACIO_ACADEMICO = (
            "ESPACIO_ACADEMICO",
            "Espacio académico",
        )

        DAAE = "DAAE", "DAAE"

        IES_DESTINO = (
            "IES_DESTINO",
            "IES destino",
        )

        CONTROL_ESCOLAR = (
            "CONTROL_ESCOLAR",
            "Control Escolar",
        )
       

        OTRO = "OTRO", "Otro"

    tipo_movilidad = models.ForeignKey(
        TipoMovilidad,
        on_delete=models.PROTECT,
        related_name="actividades_proceso",
    )

    nombre = models.CharField(
        max_length=200,
    )

    descripcion = models.TextField(
        blank=True,
    )

    etapa = models.CharField(
        max_length=20,
        choices=Etapa.choices,
    )

    responsable = models.CharField(
        max_length=30,
        choices=Responsable.choices,
    )

    obligatorio = models.BooleanField(
        default=True,
    )

    orden = models.PositiveIntegerField(
        default=0,
    )

    activo = models.BooleanField(
        default=True,
    )

    estado_expediente = models.CharField(
    max_length=30,
    choices=ExpedienteMovilidad.Estado.choices,
    )

  

    class Meta:
        ordering = ["tipo_movilidad", "orden"]

        verbose_name = "Actividad del proceso"
        verbose_name_plural = "Actividades del proceso"

    def __str__(self):
        return (
            f"{self.tipo_movilidad} - "
            f"{self.nombre}"
        )

class ActividadExpediente(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"

        EN_PROCESO = (
            "EN_PROCESO",
            "En proceso",
        )

        EN_REVISION = (
            "EN_REVISION",
            "En revisión",
        )

        COMPLETADA = (
            "COMPLETADA",
            "Completada",
        )

        REQUIERE_CORRECCION = (
            "REQUIERE_CORRECCION",
            "Requiere corrección",
        )

        NO_APLICA = (
            "NO_APLICA",
            "No aplica",
        )

        NO_REGISTRADA = (
            "NO_REGISTRADA",
            "No registrada en el sistema",
        )

    expediente = models.ForeignKey(
        ExpedienteMovilidad,
        on_delete=models.CASCADE,
        related_name="actividades",
    )

    actividad_proceso = models.ForeignKey(
        ActividadProceso,
        on_delete=models.PROTECT,
        related_name="ejecuciones",
    )

    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    fecha_limite = models.DateField(
        null=True,
        blank=True,
    )

    fecha_completada = models.DateTimeField(
        null=True,
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "actividad_proceso__orden"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "expediente",
                    "actividad_proceso",
                ],
                name="actividad_unica_por_expediente",
            )
        ]

        verbose_name = "Actividad del expediente"
        verbose_name_plural = "Actividades del expediente"

    def __str__(self):
        return (
            f"{self.expediente} - "
            f"{self.actividad_proceso.nombre}"
        )

    def save(self, *args, **kwargs):
        if self.estado == self.Estado.COMPLETADA:
            if self.fecha_completada is None:
                self.fecha_completada = timezone.now()
        else:
            self.fecha_completada = None

        super().save(*args, **kwargs)

class DocumentoExpediente(models.Model):

    class Estado(models.TextChoices):
        CARGADO = "CARGADO", "Cargado"

        EN_REVISION = (
            "EN_REVISION",
            "En revisión",
        )

        APROBADO = (
            "APROBADO",
            "Aprobado",
        )

        REQUIERE_CORRECCION = (
            "REQUIERE_CORRECCION",
            "Requiere corrección",
        )

        RECHAZADO = (
            "RECHAZADO",
            "Rechazado",
        )

    expediente = models.ForeignKey(
        ExpedienteMovilidad,
        on_delete=models.CASCADE,
        related_name="documentos",
    )

    actividad = models.ForeignKey(
        ActividadExpediente,
        on_delete=models.SET_NULL,
        related_name="documentos",
        null=True,
        blank=True,
    )

    nombre = models.CharField(
        max_length=200,
    )

    archivo = models.FileField(
        upload_to="movilidad/expedientes/",
    )

    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.CARGADO,
    )

    version = models.PositiveIntegerField(
        default=1,
    )

    fecha_carga = models.DateTimeField(
        auto_now_add=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "nombre",
            "-version",
        ]

        verbose_name = "Documento del expediente"
        verbose_name_plural = "Documentos del expediente"

    def __str__(self):
        return (
            f"{self.nombre} "
            f"(v{self.version})"
        )

class HistorialExpediente(models.Model):

    expediente = models.ForeignKey(
        ExpedienteMovilidad,
        on_delete=models.CASCADE,
        related_name="historial",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    accion = models.CharField(
        max_length=200,
    )

    descripcion = models.TextField(
        blank=True,
    )

    estado_anterior = models.CharField(
        max_length=30,
        blank=True,
    )

    estado_nuevo = models.CharField(
        max_length=30,
        blank=True,
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-fecha"]

        verbose_name = "Historial del expediente"
        verbose_name_plural = "Historial de expedientes"

    def __str__(self):
        return (
            f"{self.expediente} - "
            f"{self.accion}"
        )