from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("expedientes", "0005_documento_visibilidad"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccionSeguimiento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=200)),
                ("descripcion", models.TextField(blank=True)),
                ("responsable", models.CharField(max_length=30, choices=[("ALUMNO", "Alumno"), ("RESPONSABLE_MOVILIDAD", "Responsable de movilidad"), ("ESPACIO_ACADEMICO", "Espacio académico"), ("DAAE", "DAAE"), ("IES_DESTINO", "IES destino"), ("CONTROL_ESCOLAR", "Control Escolar"), ("OTRO", "Otro")])),
                ("estado", models.CharField(max_length=30, default="PENDIENTE", choices=[("PENDIENTE", "Pendiente"), ("EN_PROCESO", "En proceso"), ("ESPERANDO_RESPUESTA", "Esperando respuesta"), ("REQUIERE_CORRECCION", "Requiere corrección"), ("COMPLETADA", "Completada"), ("CANCELADA", "Cancelada")])),
                ("prioridad", models.CharField(max_length=12, default="NORMAL", choices=[("NORMAL", "Normal"), ("ALTA", "Alta"), ("URGENTE", "Urgente")])),
                ("fecha_limite", models.DateField(null=True, blank=True)),
                ("proximo_seguimiento", models.DateField(null=True, blank=True)),
                ("visible_alumno", models.BooleanField(default=False, help_text="Solo si el contenido se puede mostrar al alumno; nunca incluye archivos reservados")),
                ("observaciones", models.TextField(blank=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                ("fecha_cierre", models.DateTimeField(null=True, blank=True)),
                ("actividad", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acciones_seguimiento", to="expedientes.actividadexpediente")),
                ("documento", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acciones_seguimiento", to="expedientes.documentoexpediente")),
                ("expediente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="acciones_seguimiento", to="expedientes.expedientemovilidad")),
                ("encargado_seguimiento", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acciones_movilidad_supervisadas", to=settings.AUTH_USER_MODEL)),
                ("creado_por", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acciones_movilidad_creadas", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["proximo_seguimiento", "fecha_limite", "pk"], "verbose_name": "Acción de seguimiento", "verbose_name_plural": "Acciones de seguimiento"},
        ),
        migrations.CreateModel(
            name="HistorialAccion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("descripcion", models.TextField()),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                ("accion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="historial", to="expedientes.accionseguimiento")),
                ("usuario", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fecha", "-pk"], "verbose_name": "Historial de acción", "verbose_name_plural": "Historial de acciones"},
        ),
        migrations.CreateModel(
            name="RecordatorioSeguimiento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("destinatario", models.CharField(max_length=200, help_text="Destino o área verificados por quien redacta; no presume dirección institucional")),
                ("canal", models.CharField(max_length=30, default="CORREO", choices=[("CORREO", "Correo electrónico"), ("OTRO", "Otro canal")])),
                ("asunto", models.CharField(max_length=200)),
                ("mensaje", models.TextField()),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("estado", models.CharField(max_length=20, default="BORRADOR", editable=False, choices=[("BORRADOR", "Borrador sin enviar")])),
                ("accion", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name="recordatorios", to="expedientes.accionseguimiento")),
                ("actividad", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name="recordatorios", to="expedientes.actividadexpediente")),
                ("creado_por", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fecha_creacion", "-pk"], "verbose_name": "Borrador de recordatorio", "verbose_name_plural": "Borradores de recordatorios"},
        ),
    ]
