from django.db import models

# Create your models here.

from convocatorias.models import Convocatoria, TipoMovilidad


class CategoriaFAQ(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Categoría de FAQ"
        verbose_name_plural = "Categorías de FAQ"

    def __str__(self):
        return self.nombre


class Publicacion(models.Model):
    class Categoria(models.TextChoices):
        INFORMACION = "INFORMACION", "Información"
        AVISO = "AVISO", "Aviso"
        URGENTE = "URGENTE", "Urgente"

    titulo = models.CharField(max_length=200)
    contenido = models.TextField()

    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.INFORMACION,
    )

    fecha_publicacion = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    publicada = models.BooleanField(default=False)
    destacada = models.BooleanField(default=False)

    convocatoria = models.ForeignKey(
        Convocatoria,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="publicaciones",
    )

    tipo_movilidad = models.ForeignKey(
        TipoMovilidad,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="publicaciones",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_publicacion", "-creado_en"]

    def __str__(self):
        return self.titulo


class PreguntaFrecuente(models.Model):
    categoria = models.ForeignKey(
        CategoriaFAQ,
        on_delete=models.PROTECT,
        related_name="preguntas",
    )

    pregunta = models.CharField(max_length=300)
    respuesta = models.TextField()

    tipo_movilidad = models.ForeignKey(
        TipoMovilidad,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="preguntas_frecuentes",
    )

    fuente_oficial_url = models.URLField(blank=True)

    orden = models.PositiveIntegerField(default=0)
    publicada = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria__orden", "orden", "pregunta"]
        verbose_name = "Pregunta frecuente"
        verbose_name_plural = "Preguntas frecuentes"

    def __str__(self):
        return self.pregunta