from django.db import models

# Create your models here.



class TipoMovilidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Tipo de movilidad"
        verbose_name_plural = "Tipos de movilidad"

    def __str__(self):
        return self.nombre


class Convocatoria(models.Model):
    class Ciclo(models.TextChoices):
        PRIMAVERA = "PRIMAVERA", "Primavera"
        OTONO = "OTONO", "Otoño"

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PUBLICADA = "PUBLICADA", "Publicada"
        CERRADA = "CERRADA", "Cerrada"
        ARCHIVADA = "ARCHIVADA", "Archivada"

    tipo_movilidad = models.ForeignKey(
        TipoMovilidad,
        on_delete=models.PROTECT,
        related_name="convocatorias",
    )

    titulo = models.CharField(max_length=200)
    ciclo = models.CharField(max_length=20, choices=Ciclo.choices)
    anio = models.PositiveSmallIntegerField()
    resumen = models.CharField(max_length=300, blank=True)
    descripcion = models.TextField(blank=True)

    fecha_publicacion = models.DateTimeField(null=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
    )

    destacada = models.BooleanField(default=False)
    fuente_oficial_url = models.URLField(blank=True)

    documento_oficial = models.FileField(
        upload_to="convocatorias/",
        blank=True,
        null=True,
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-anio", "ciclo", "titulo"]

    def __str__(self):
        return self.titulo


class Requisito(models.Model):
    convocatoria = models.ForeignKey(
        Convocatoria,
        on_delete=models.CASCADE,
        related_name="requisitos",
    )

    texto = models.TextField()
    obligatorio = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]

    def __str__(self):
        return self.texto[:80]


class FechaImportante(models.Model):
    convocatoria = models.ForeignKey(
        Convocatoria,
        on_delete=models.CASCADE,
        related_name="fechas_importantes",
    )

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha = models.DateField()
    hora = models.TimeField(null=True, blank=True)
    es_fecha_limite = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["fecha", "hora", "orden"]

    def __str__(self):
        return f"{self.titulo} - {self.fecha}"


class IES(models.Model):
    nombre = models.CharField(max_length=250)
    pais = models.CharField(max_length=100)
    estado_region = models.CharField(max_length=150, blank=True)
    sitio_web = models.URLField(blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["pais", "nombre"]
        verbose_name = "IES"
        verbose_name_plural = "IES"

    def __str__(self):
        return self.nombre


class ConvocatoriaIES(models.Model):
    convocatoria = models.ForeignKey(
        Convocatoria,
        on_delete=models.CASCADE,
        related_name="instituciones",
    )

    ies = models.ForeignKey(
        IES,
        on_delete=models.PROTECT,
        related_name="convocatorias",
    )

    observaciones = models.TextField(blank=True)
    restricciones = models.TextField(blank=True)
    disponible = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        #verbose_name = "IES de convocatoria"
        verbose_name_plural = "convocatorias de IES"
        constraints = [
            models.UniqueConstraint(
                fields=["convocatoria", "ies"],
                name="unique_ies_por_convocatoria",
            )
        ]
        ordering = ["orden", "ies__nombre"]

    def __str__(self):
        return f"{self.convocatoria} - {self.ies}"