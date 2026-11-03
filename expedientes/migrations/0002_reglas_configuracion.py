from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("expedientes", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReglaActividadConvocatoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estado_configuracion", models.CharField(choices=[("SIN_DEFINIR", "Sin definir"), ("DEFINIDA", "Definida")], default="SIN_DEFINIR", max_length=20)),
                ("politica", models.CharField(choices=[("BLOQUEANTE", "Bloqueante"), ("CONDICIONAL", "Condicional"), ("SEGUIMIENTO", "Seguimiento")], default="SEGUIMIENTO", max_length=20)),
                ("condicion_aplicabilidad", models.TextField(blank=True)),
                ("fundamento", models.TextField(blank=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("actividad_proceso", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reglas_convocatorias", to="expedientes.actividadproceso")),
                ("convocatoria", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reglas_actividades", to="convocatorias.convocatoria")),
            ],
            options={
                "verbose_name": "Regla de actividad de convocatoria",
                "verbose_name_plural": "Reglas de actividades de convocatoria",
                "constraints": [models.UniqueConstraint(fields=("convocatoria", "actividad_proceso"), name="regla_unica_convocatoria_actividad")],
            },
        ),
        migrations.CreateModel(
            name="ReglaActividadExpediente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("politica", models.CharField(choices=[("BLOQUEANTE", "Bloqueante"), ("CONDICIONAL", "Condicional"), ("SEGUIMIENTO", "Seguimiento")], max_length=20)),
                ("condicion_aplicabilidad", models.TextField(blank=True)),
                ("fundamento", models.TextField(blank=True)),
                ("aplicabilidad", models.CharField(choices=[("SIN_RESOLVER", "Sin resolver"), ("APLICA", "Aplica"), ("NO_APLICA", "No aplica")], default="SIN_RESOLVER", max_length=20)),
                ("justificacion_no_aplica", models.TextField(blank=True)),
                ("validado_en", models.DateTimeField(blank=True, null=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actividad_expediente", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="regla_asignada", to="expedientes.actividadexpediente")),
                ("regla_origen", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="copias_expedientes", to="expedientes.reglaactividadconvocatoria")),
                ("validado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reglas_movilidad_validadas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Regla asignada a actividad de expediente",
                "verbose_name_plural": "Reglas asignadas a actividades de expedientes",
            },
        ),
    ]
